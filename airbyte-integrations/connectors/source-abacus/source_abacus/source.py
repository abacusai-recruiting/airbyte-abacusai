#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

import logging
from typing import Any, Iterator, List, Mapping, MutableMapping, Optional, Tuple

from airbyte_cdk.models import (
    AirbyteCatalog,
    AirbyteConnectionStatus,
    AirbyteMessage,
    AirbyteStream,
    ConfiguredAirbyteCatalog,
    Status,
    SyncMode,
)
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.connector_state_manager import ConnectorStateManager
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.utils.schema_helpers import split_config
from airbyte_cdk.utils.event_timing import create_timer

from .abacus_feature_group import AbacusFeatureGroupReader
from .streams import AbacusFeatureGroupStream


class SourceAbacus(AbstractSource):
    """This source helps to sync data from Abacus AI feature groups"""

    def check_connection(self, logger: logging.Logger, config: Mapping[str, Any]) -> Tuple[bool, Optional[Any]]:
        pass

    def _as_airbyte_record(self, stream_name: str, data: Mapping[str, Any]):
        return data

    @property
    def get_typed_schema(self) -> object:
        """Static schema for feature groups"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {"feature_group_id": {"type": "string"}},
        }

    def check(self, logger: logging.Logger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            reader = AbacusFeatureGroupReader(logger, config)
            client = reader.get_abacus_client()
            feature_groups = client.list_feature_groups()
            # Try to get at least one feature group to verify connection
            if feature_groups:
                next(iter(feature_groups))
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except StopIteration:
            logger.info("The credentials you provided are valid, but no feature groups were found in Abacus AI.")
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {str(e)}")

    def discover(self, logger: logging.Logger, config: Mapping[str, Any]) -> AirbyteCatalog:
        reader = AbacusFeatureGroupReader(logger, config)
        feature_groups = reader.get_feature_groups()

        streams = []
        for feature_group in feature_groups:
            stream_name = feature_group.feature_group_id
            stream = AirbyteStream(
                name=stream_name,
                json_schema=self.get_typed_schema,
                supported_sync_modes=[SyncMode.full_refresh, SyncMode.incremental],
                source_defined_cursor=True,
                default_cursor_field=["feature_group_id"],
            )
            streams.append(stream)
        logger.info(f"Total {len(streams)} streams found.")
        return AirbyteCatalog(streams=streams)

    def streams(self, logger: logging.Logger, config: Mapping[str, Any]) -> List[Stream]:
        """
        :param config: The user-provided configuration as specified by the source's spec.
        Any stream construction related operation should happen here.
        :return: A list of the streams in this source connector.
        """

        try:
            reader = AbacusFeatureGroupReader(logger, config)
            feature_groups = reader.get_feature_groups()

            streams = []
            for feature_group in feature_groups:
                stream_name = feature_group.feature_group_id
                stream = AbacusFeatureGroupStream(stream_name=stream_name, reader=reader)
                streams.append(stream)
            return streams
        except Exception as e:
            raise Exception(f"An exception occurred: {str(e)}")

    def read(
        self, logger: logging.Logger, config: Mapping[str, Any], catalog: ConfiguredAirbyteCatalog, state: MutableMapping[str, Any] = None
    ) -> Iterator[AirbyteMessage]:
        """
        This method is overridden to check whether the stream `quotes` exists in the source, if not skip reading that stream.
        """
        stream_instances = {s.name: s for s in self.streams(logger=logger, config=config)}
        state_manager = ConnectorStateManager(stream_instance_map=stream_instances, state=state)
        logger.info(f"Starting syncing {self.name}")
        config, internal_config = split_config(config)
        self._stream_to_instance_map = stream_instances
        with create_timer(self.name) as timer:
            for configured_stream in catalog.streams:
                stream_instance = stream_instances.get(configured_stream.stream.name)
                stream_instance.cursor_field = configured_stream.cursor_field
                if not stream_instance and configured_stream.stream.name == "quotes":
                    logger.warning("Stream `quotes` does not exist in the source. Skip reading `quotes` stream.")
                    continue
                if not stream_instance:
                    raise KeyError(
                        f"The requested stream {configured_stream.stream.name} was not found in the source. Available streams: {stream_instances.keys()}"
                    )

                try:
                    yield from self._read_stream(
                        logger=logger,
                        stream_instance=stream_instance,
                        configured_stream=configured_stream,
                        state_manager=state_manager,
                        internal_config=internal_config,
                    )
                except Exception as e:
                    logger.exception(f"Encountered an exception while reading stream {self.name}")
                    raise e
                finally:
                    logger.info(f"Finished syncing {self.name}")
                    logger.info(timer.report())

        logger.info(f"Finished syncing {self.name}")
