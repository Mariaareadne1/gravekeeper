"""The GCP and Azure connectors are interface skeletons: they must implement the
Connector contract and fail loudly (not silently return empty) until wired."""

import pytest

from gravekeeper.connectors.azure import AzureConnector
from gravekeeper.connectors.base import Connector, ConnectorError
from gravekeeper.connectors.gcp import GCPConnector
from gravekeeper.models import Source


@pytest.mark.parametrize("cls,source", [(GCPConnector, Source.gcp), (AzureConnector, Source.azure)])
def test_stub_connectors_implement_interface(cls, source):
    conn = cls(credentials={})
    assert isinstance(conn, Connector)
    assert conn.source is source


@pytest.mark.parametrize("cls", [GCPConnector, AzureConnector])
def test_stub_connectors_fail_loudly(cls):
    conn = cls(credentials={})
    with pytest.raises(ConnectorError):
        conn.validate_credentials()
    with pytest.raises(ConnectorError):
        conn.discover()
