#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from datetime import datetime
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional

from airbyte_cdk.models import AirbyteMessage, AirbyteRecordMessage, SyncMode, Type
from airbyte_cdk.sources.streams import Stream


class AbacusFeatureGroupStream(Stream):
    primary_key = None
    cursor_field = None

    def __init__(self, stream_name: str, reader: object, **kwargs):
        super(Stream, self).__init__(**kwargs)
        self.stream_name = stream_name
        self.abacus_feature_group_reader = reader
        self._state: Optional[Mapping[str, Any]] = None

    @property
    def name(self):
        return self.stream_name

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]):
        return {self.cursor_field[0]: latest_record.data.get(self.cursor_field[0])}

    def _update_state(self, latest_cursor):
        self._state = latest_cursor

    def read_records(
        self,
        sync_mode: SyncMode,
        cursor_field: List[str] = None,
        stream_slice: Mapping[str, Any] = None,
        stream_state: Mapping[str, Any] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Create and retrieve the feature group data.
        Read and yield the feature group records.
        """
        if sync_mode == SyncMode.full_refresh:
            for row in self.abacus_feature_group_reader.read_feature_group(self.stream_name):
                yield AirbyteMessage(
                    type=Type.RECORD,
                    record=AirbyteRecordMessage(stream=self.stream_name, data=row, emitted_at=int(datetime.now().timestamp()) * 1000),
                )
        if sync_mode == SyncMode.incremental:
            cursor_field = cursor_field[0] if cursor_field else "feature_group_id"
            cursor_value = 0 if stream_state.get(cursor_field) is None else stream_state.get(cursor_field)
            # For incremental sync, we would need to implement filtering based on cursor
            # This is a simplified implementation - actual implementation would depend on Abacus AI capabilities
            rows = list(self.abacus_feature_group_reader.read_feature_group(self.stream_name))
            for row in rows:
                yield AirbyteMessage(
                    type=Type.RECORD,
                    record=AirbyteRecordMessage(stream=self.stream_name, data=row, emitted_at=int(datetime.now().timestamp()) * 1000),
                )

            if len(rows) > 0:
                self._update_state(latest_cursor=rows[-1].get(cursor_field, cursor_value))
