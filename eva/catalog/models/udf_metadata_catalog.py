# coding=utf-8
# Copyright 2018-2022 EVA
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
from dataclasses import dataclass

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from eva.catalog.models.base_model import BaseModel


class UdfMetadataCatalog(BaseModel):
    """
    The `UdfMetadataCatalog` catalog stores information about the metadata of user-defined functions (UDFs).
    Metadata is implemented a key-value pair that can be used to store additional information about the UDF.
    It maintains the following information for each attribute:
        `_row_id:` an autogenerated identifier
        `_key: ` key/identifier of the metadata (as a string)
        `_value:` value of the metadata (as a string)
        `_udf_id:` the `_row_id` of the `UdfCatalog` entry to which the attribute belongs
    """

    __tablename__ = "udf_metadata_catalog"

    _key = Column("key", String(100))
    _value = Column("value", String(100))
    _udf_id = Column("udf_id", Integer, ForeignKey("udf_catalog._row_id"))

    __table_args__ = (UniqueConstraint("key", "udf_id"), {})

    # Foreign key dependency with the udf catalog
    _udf = relationship("UdfCatalog", back_populates="_metadata")

    def __init__(self, key: str, value: str, udf_id: int):
        self._key = key
        self._value = value
        self._udf_id = udf_id

    def as_dataclass(self) -> "UdfMetadataCatalogEntry":
        return UdfMetadataCatalogEntry(
            row_id=self._row_id,
            key=self._key,
            value=self._value,
            udf_id=self._udf_id,
            udf_name=self._udf._name,
        )


@dataclass(unsafe_hash=True)
class UdfMetadataCatalogEntry:
    """Class decouples the `UdfMetadataCatalog` from the sqlalchemy.
    This is done to ensure we don't expose the sqlalchemy dependencies beyond catalog service. Further, sqlalchemy does not allow sharing of objects across threads.
    """

    key: str
    value: str
    udf_id: int = None
    udf_name: str = None
    row_id: int = None

    def display_format(self):
        return f"{self.udf_name} - {self.key}: {self.value}"
