from __future__ import annotations

import uuid

import pytest

from bioimage_mcp.artifacts.memory import MemoryArtifactStore
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.adapters.matplotlib import (
    MatplotlibAdapter,
    SessionObjectNotFoundError,
)


@pytest.fixture
def memory_store():
    return MemoryArtifactStore()


@pytest.fixture
def adapter():
    return MatplotlibAdapter()


def test_obj_uri_includes_session_id():
    """R2.5: Verify obj:// URI format includes session_id."""
    from bioimage_mcp.artifacts.memory import parse_mem_uri

    # Expected format: obj://{session_id}/{env_id}/{artifact_id}
    test_uri = "obj://my-session-123/base/artifact-abc"
    session_id, env_id, artifact_id = parse_mem_uri(test_uri)

    assert session_id == "my-session-123"
    assert env_id == "base"
    assert artifact_id == "artifact-abc"


def test_reject_unregistered_obj_ref(adapter, memory_store):
    """R2.5: Verify error when ref_id not in store."""
    session_id = "session-1"
    env_id = "base"

    # Create an input with an obj:// URI that is NOT in the store
    ref_id = str(uuid.uuid4())
    uri = f"obj://{session_id}/{env_id}/{ref_id}"

    inputs = [
        {
            "ref_id": ref_id,
            "type": "ObjectRef",
            "uri": uri,
        }
    ]

    # Any function that uses inputs, like Axes.imshow
    fn_id = "base.matplotlib.Axes.imshow"

    with pytest.raises(SessionObjectNotFoundError) as excinfo:
        adapter.execute(
            fn_id=fn_id,
            inputs=inputs,
            params={"X": "some-data"},
            session_id=session_id,
            memory_store=memory_store,
        )

    assert (
        f"Object reference '{ref_id}' (URI: {uri}) is not registered to session '{session_id}'"
        in str(excinfo.value)
    )


def test_reject_cross_session_ref(adapter, memory_store):
    """R2.5: Verify error when ref belongs to different session."""
    session_a = "session-a"
    session_b = "session-b"
    env_id = "base"

    # Register an object in session_a
    ref_id = str(uuid.uuid4())
    uri_a = f"obj://{session_a}/{env_id}/{ref_id}"
    ref = ArtifactRef(
        ref_id=ref_id,
        type="ObjectRef",
        uri=uri_a,
    )
    memory_store.register(ref)

    # Try to use it in session_b
    inputs = [
        {
            "ref_id": ref_id,
            "type": "ObjectRef",
            "uri": uri_a,
        }
    ]

    fn_id = "base.matplotlib.Axes.imshow"

    with pytest.raises(SessionObjectNotFoundError) as excinfo:
        adapter.execute(
            fn_id=fn_id,
            inputs=inputs,
            params={"X": "some-data"},
            session_id=session_b,
            memory_store=memory_store,
        )

    # Match the actual implementation message for cross-session
    assert (
        f"Object reference '{ref_id}' (URI: {uri_a}) is registered "
        f"to a different session ('{session_a}')" in str(excinfo.value)
    )
    assert f"not the active session '{session_b}'" in str(excinfo.value)


def test_allow_registered_same_session_ref(adapter, memory_store):
    """R2.5: Verify valid refs work."""
    # This might actually fail because we haven't updated matplotlib_ops yet,
    # but the validation should pass if we register it correctly.
    # However, it will then try to call the real matplotlib_ops.imshow which might fail
    # for other reasons in a unit test environment.

    session_id = "session-1"
    env_id = "base"

    # Register an object in session-1
    ref_id = str(uuid.uuid4())
    uri = f"obj://{session_id}/{env_id}/{ref_id}"
    ref = ArtifactRef(
        ref_id=ref_id,
        type="ObjectRef",
        uri=uri,
    )
    memory_store.register(ref)

    # Mock the underlying op to avoid real matplotlib execution if it's too heavy
    # for a unit test, but here we just want to see if it passes the validation.
    # We can use a simpler op or just check if it gets PAST validation.

    # For now, let's just assert it doesn't raise SessionObjectNotFoundError
    inputs = [
        {
            "ref_id": ref_id,
            "type": "ObjectRef",
            "uri": uri,
        }
    ]

    fn_id = "base.matplotlib.Axes.imshow"

    # It will probably fail with a real ValueError from imshow (missing axes)
    # but NOT with SessionObjectNotFoundError.
    try:
        adapter.execute(
            fn_id=fn_id,
            inputs=inputs,
            params={"X": "some-data"},
            session_id=session_id,
            memory_store=memory_store,
        )
    except SessionObjectNotFoundError:
        pytest.fail("Should not have raised SessionObjectNotFoundError")
    except Exception:
        # Other errors are fine for this test as long as validation passed
        pass


def test_reject_when_memory_store_none(adapter):
    """Issue 1: Verify rejection when memory_store is None but obj:// input present."""
    session_id = "session-1"
    ref_id = str(uuid.uuid4())
    uri = f"obj://{session_id}/base/{ref_id}"

    inputs = [
        {
            "ref_id": ref_id,
            "type": "ObjectRef",
            "uri": uri,
        }
    ]

    with pytest.raises(SessionObjectNotFoundError) as excinfo:
        adapter.execute(
            fn_id="base.matplotlib.Axes.imshow",
            inputs=inputs,
            params={"X": "data"},
            session_id=session_id,
            memory_store=None,
        )

    assert "memory store not available" in str(excinfo.value)


def test_reject_when_ref_id_missing(adapter, memory_store):
    """Issue 2: Verify rejection when ref_id is missing from obj:// input."""
    session_id = "session-1"
    uri = f"obj://{session_id}/base/{str(uuid.uuid4())}"

    inputs = [
        {
            # Missing ref_id
            "type": "ObjectRef",
            "uri": uri,
        }
    ]

    with pytest.raises(SessionObjectNotFoundError) as excinfo:
        adapter.execute(
            fn_id="base.matplotlib.Axes.imshow",
            inputs=inputs,
            params={"X": "data"},
            session_id=session_id,
            memory_store=memory_store,
        )

    assert "missing ref_id" in str(excinfo.value)


def test_reject_obj_ref_in_params(adapter, memory_store):
    """Verify obj:// refs in params are also validated."""
    session_id = "my-session"

    # Try to sneak an unregistered ref through params
    malicious_ref = {
        "ref_id": "stolen-ref",
        "uri": "obj://other-session/base/stolen-ref",
        "type": "ObjectRef",
    }

    with pytest.raises(SessionObjectNotFoundError) as excinfo:
        adapter.execute(
            fn_id="base.matplotlib.Axes.add_patch",
            inputs=[],
            params={"patch": malicious_ref},
            session_id=session_id,
            memory_store=memory_store,
        )

    # If it was unregistered, it should fail with "is not registered" or
    # "is registered to a different session"
    # In this case, it's not registered at all in our memory_store
    assert "is not registered to session 'my-session'" in str(excinfo.value)


def test_reject_obj_ref_in_nested_params(adapter, memory_store):
    """Verify obj:// refs in nested params are also validated."""
    session_id = "my-session"

    malicious_ref = {
        "ref_id": "stolen-ref",
        "uri": "obj://other-session/base/stolen-ref",
        "type": "ObjectRef",
    }

    with pytest.raises(SessionObjectNotFoundError):
        adapter.execute(
            fn_id="base.matplotlib.Axes.plot",
            inputs=[],
            params={"extra_args": {"patches": [malicious_ref]}},
            session_id=session_id,
            memory_store=memory_store,
        )
