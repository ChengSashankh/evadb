# coding=utf-8
# Copyright 2018-2023 EvaDB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

import pandas as pd
from gptcache.embedding import Onnx
from gptcache.manager import get_data_manager, CacheBase, VectorBase
from gptcache.similarity_evaluation import SearchDistanceEvaluation
from retry import retry
from gptcache.adapter.openai import cache_openai_chat_complete
from gptcache import cache

from evadb.catalog.catalog_type import NdArrayType
from evadb.functions.abstract.abstract_function import AbstractFunction
from evadb.functions.decorators.decorators import forward, setup
from evadb.functions.decorators.io_descriptors.data_types import PandasDataframe
from evadb.utils.generic_utils import try_to_import_openai

_VALID_CHAT_COMPLETION_MODEL = [
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0301",
]


class ChatGPTWithCache(AbstractFunction):
    """
    Arguments:
        model (str) : ID of the OpenAI model to use. Refer to '_VALID_CHAT_COMPLETION_MODEL' for a list of supported models.
        temperature (float) : Sampling temperature to use in the model. Higher value results in a more random output.

    Input Signatures:
        query (str)   : The task / question that the user wants the model to accomplish / respond.
        content (str) : Any relevant context that the model can use to complete its tasks and generate the response.
        prompt (str)  : An optional prompt that can be passed to the model. It can contain instructions to the model,
                        or a set of examples to help the model generate a better response.
                        If not provided, the system prompt defaults to that of an helpful assistant that accomplishes user tasks.

    Output Signatures:
        response (str) : Contains the response generated by the model based on user input. Any errors encountered
                         will also be passed in the response.

    Example Usage:
        Assume we have the transcripts for a few videos stored in a table 'video_transcripts' in a column named 'text'.
        If the user wants to retrieve the summary of each video, the ChatGPT function can be used as:

            query = "Generate the summary of the video"
            cursor.table("video_transcripts").select(f"ChatGPT({query}, text)")

        In the above function invocation, the 'query' passed would be the user task to generate video summaries, and the
        'content' passed would be the video transcripts that need to be used in order to generate the summary. Since
        no prompt is passed, the default system prompt will be used.

        Now assume the user wants to create the video summary in 50 words and in French. Instead of passing these instructions
        along with each query, a prompt can be set as such:

            prompt = "Generate your responses in 50 words or less. Also, generate the response in French."
            cursor.table("video_transcripts").select(f"ChatGPT({query}, text, {prompt})")

        In the above invocation, an additional argument is passed as prompt. While the query and content arguments remain
        the same, the 'prompt' argument will be set as a system message in model params.

        Both of the above cases would generate a summary for each row / video transcript of the table in the response.
    """

    @property
    def name(self) -> str:
        return "ChatGPTWithCache"

    @setup(cacheable=False, function_type="chat-completion", batchable=True)
    def setup(
        self,
        model="gpt-3.5-turbo",
        temperature: float = 0,
        openai_api_key="",
    ) -> None:
        assert model in _VALID_CHAT_COMPLETION_MODEL, f"Unsupported ChatGPTWithCache {model}"
        self.model = model
        self.temperature = temperature
        self.openai_api_key = openai_api_key

        onnx = Onnx()
        data_manager = get_data_manager(CacheBase("sqlite"), VectorBase("faiss", dimension=onnx.dimension))
        cache.init(
            embedding_func=onnx.to_embeddings,
            data_manager=data_manager,
            similarity_evaluation=SearchDistanceEvaluation(),
        )
        cache.set_openai_key()

    @forward(
        input_signatures=[
            PandasDataframe(
                columns=["query", "content", "prompt"],
                column_types=[
                    NdArrayType.STR,
                    NdArrayType.STR,
                    NdArrayType.STR,
                ],
                column_shapes=[(1,), (1,), (None,)],
            )
        ],
        output_signatures=[
            PandasDataframe(
                columns=["response"],
                column_types=[
                    NdArrayType.STR,
                ],
                column_shapes=[(1,)],
            )
        ],
    )
    def forward(self, text_df):
        print ("Starting forward")
        try_to_import_openai()
        from openai import OpenAI
        print ("Imported OpenAI")

        api_key = self.openai_api_key
        if len(self.openai_api_key) == 0:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        assert (
            len(api_key) != 0
        ), "Please set your OpenAI API key using SET OPENAI_API_KEY = 'sk-' or environment variable (OPENAI_API_KEY)"

        client = OpenAI(api_key=api_key)
        print ("Initialized OpenAI client")

        @retry(tries=6, delay=20)
        def completion_with_backoff(**kwargs):
            print(f"Calling completion api with: {kwargs}")
            return cache_openai_chat_complete(client, **kwargs)

        queries = text_df[text_df.columns[0]]
        content = text_df[text_df.columns[0]]
        if len(text_df.columns) > 1:
            queries = text_df.iloc[:, 0]
            content = text_df.iloc[:, 1]

        prompt = None
        if len(text_df.columns) > 2:
            prompt = text_df.iloc[0, 2]

        # openai api currently supports answers to a single prompt only
        # so this function is designed for that
        results = []

        for query, content in zip(queries, content):
            params = {
                "model": self.model,
                "temperature": self.temperature,
                "messages": [],
            }

            def_sys_prompt_message = {
                "role": "system",
                "content": prompt
                if prompt is not None
                else "You are a helpful assistant that accomplishes user tasks.",
            }

            params["messages"].append(def_sys_prompt_message)
            params["messages"].extend(
                [
                    {
                        "role": "user",
                        "content": f"Here is some context : {content}",
                    },
                    {
                        "role": "user",
                        "content": f"Complete the following task: {query}",
                    },
                ],
            )

            print ("Calling for prompt")
            response = completion_with_backoff(**params)
            print ("Done with prompt")
            answer = response.choices[0].message.content
            results.append(answer)

        df = pd.DataFrame({"response": results})

        return df
