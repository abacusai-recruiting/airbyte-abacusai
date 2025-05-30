#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

import logging
from typing import Iterable, List

from abacusai import ApiClient, FeatureGroup
from . import constants


class AbacusFeatureGroupReader:
    """
    This reader reads data from the given feature group.

    Attributes
    ----------
    logger : AirbyteLogger
        Airbyte's Logger instance
    api_key : str
        The Abacus API Key to use for authentication.

    Methods
    -------
    get_abacus_client()
        Returns Abacus client.

    get_feature_groups()
        Fetches all feature groups from Abacus AI

    read_feature_group()
        Reads data from an Abacus feature group

    """

    def __init__(self, logger: logging.Logger, config: dict):
        """
        Parameters
        ----------
        config : dict
            Airbyte's configuration object

        """
        self.logger = logger
        self.api_key = config[constants.abacus_api_key_name]

    def get_abacus_client(self) -> ApiClient:
        """
        Returns Abacus AI client using the API key.
        The client facilitates interaction with Abacus AI services.

        """
        try:
            return ApiClient(api_key=self.api_key)
        except Exception as e:
            raise Exception(f"An exception occurred: {str(e)}")

    def get_feature_group(self, feature_group_id: str) -> FeatureGroup:
        """
        Returns Abacus feature group client for a specific feature group.

        Parameters
        ----------
        feature_group_id : str
            feature group ID for which you would like to create a feature group client.

        """
        try:
            if not feature_group_id:
                raise Exception("An exception occurred: feature group ID is not valid.")
            client = self.get_abacus_client()
            return client.describe_feature_group(feature_group_id)
        except Exception as e:
            raise Exception(f"An exception occurred: {str(e)}")

    def get_feature_groups(self) -> List[FeatureGroup]:
        """
        Fetches all feature groups from Abacus AI and returns them.
        """
        try:
            client = self.get_abacus_client()
            feature_groups = client.list_feature_groups()
            return feature_groups
        except Exception as e:
            raise Exception(f"An exception occurred: {str(e)}")

    def read_feature_group(self, feature_group_id: str, limit: int = None) -> Iterable:
        """
        Reads data from an Abacus feature group.

        Parameters
        ----------
        feature_group_id : str
            feature group ID to read data from.

        limit : int
            optional limit on the number of records to return
        """
        try:
            client = self.get_abacus_client()
            feature_group = client.describe_feature_group(feature_group_id)
            # Get the data from the feature group
            data = feature_group.get_data(limit=limit)
            return data
        except Exception as e:
            raise Exception(f"An exception occurred: {str(e)}")
