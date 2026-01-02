"""Tests for lineage applications in dependency exports."""
from datetime import date

import pytest

from app.api.model_dependencies import build_lineage_paths
from app.models.map_application import MapApplication
from app.models.model import Model
from app.models.model_application import ModelApplication
from app.models.model_feed_dependency import ModelFeedDependency
from app.models.taxonomy import Taxonomy, TaxonomyValue


@pytest.fixture
def dependency_taxonomy(db_session):
    """Create Model Dependency Type taxonomy."""
    taxonomy = Taxonomy(name="Model Dependency Type", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    input_data = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="INPUT_DATA",
        label="Input Data",
        sort_order=1
    )
    score = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="SCORE",
        label="Score/Output",
        sort_order=2
    )
    db_session.add_all([input_data, score])
    db_session.commit()

    return {"input_data": input_data, "score": score}


@pytest.fixture
def application_relationship_taxonomy(db_session):
    """Create Application Relationship Type taxonomy."""
    taxonomy = Taxonomy(name="Application Relationship Type", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    data_source = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="DATA_SOURCE",
        label="Data Source",
        sort_order=1
    )
    output_consumer = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="OUTPUT_CONSUMER",
        label="Output Consumer",
        sort_order=2
    )
    db_session.add_all([data_source, output_consumer])
    db_session.commit()

    return {"data_source": data_source, "output_consumer": output_consumer}


def _create_model(db_session, owner_id, usage_frequency_id, name: str) -> Model:
    model = Model(
        model_name=name,
        description=f"{name} for lineage testing",
        development_type="In-House",
        status="In Development",
        owner_id=owner_id,
        row_approval_status="Draft",
        submitted_by_user_id=owner_id,
        usage_frequency_id=usage_frequency_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def lineage_models(db_session, admin_user, usage_frequency):
    """Create a chain of models for lineage testing."""
    model_a = _create_model(db_session, admin_user.user_id, usage_frequency["daily"].value_id, "Model A")
    model_b = _create_model(db_session, admin_user.user_id, usage_frequency["daily"].value_id, "Model B")
    model_c = _create_model(db_session, admin_user.user_id, usage_frequency["daily"].value_id, "Model C")
    return {"a": model_a, "b": model_b, "c": model_c}


@pytest.fixture
def lineage_applications(db_session):
    """Create MAP applications for lineage testing."""
    apps = [
        MapApplication(
            application_code="APP-UP-B",
            application_name="Upstream App for B",
            department="IT",
            status="Active"
        ),
        MapApplication(
            application_code="APP-DOWN-B",
            application_name="Downstream App for B",
            department="Risk",
            status="Active"
        ),
        MapApplication(
            application_code="APP-UP-C",
            application_name="Upstream App for C",
            department="Finance",
            status="Active"
        ),
    ]
    db_session.add_all(apps)
    db_session.commit()
    return apps


def test_lineage_includes_applications_recursively(
    client,
    admin_headers,
    db_session,
    dependency_taxonomy,
    application_relationship_taxonomy,
    lineage_models,
    lineage_applications,
):
    """Ensure lineage attaches upstream/downstream applications to every node in the chain."""
    model_a = lineage_models["a"]
    model_b = lineage_models["b"]
    model_c = lineage_models["c"]

    # Build model dependencies: C -> B -> A
    db_session.add_all([
        ModelFeedDependency(
            feeder_model_id=model_b.model_id,
            consumer_model_id=model_a.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            description="B provides input to A",
            is_active=True,
        ),
        ModelFeedDependency(
            feeder_model_id=model_c.model_id,
            consumer_model_id=model_b.model_id,
            dependency_type_id=dependency_taxonomy["input_data"].value_id,
            description="C provides input to B",
            is_active=True,
        ),
    ])

    # Attach applications to B (upstream + downstream) and C (upstream)
    db_session.add_all([
        ModelApplication(
            model_id=model_b.model_id,
            application_id=lineage_applications[0].application_id,
            relationship_type_id=application_relationship_taxonomy["data_source"].value_id,
            relationship_direction="UPSTREAM",
            description="Feeds B",
            effective_date=date(2025, 1, 1),
        ),
        ModelApplication(
            model_id=model_b.model_id,
            application_id=lineage_applications[1].application_id,
            relationship_type_id=application_relationship_taxonomy["output_consumer"].value_id,
            relationship_direction="DOWNSTREAM",
            description="Consumes from B",
            effective_date=date(2025, 1, 1),
        ),
        ModelApplication(
            model_id=model_c.model_id,
            application_id=lineage_applications[2].application_id,
            relationship_type_id=application_relationship_taxonomy["data_source"].value_id,
            relationship_direction="UPSTREAM",
            description="Feeds C",
            effective_date=date(2025, 1, 1),
        ),
        ModelApplication(
            model_id=model_b.model_id,
            application_id=lineage_applications[2].application_id,
            relationship_type_id=application_relationship_taxonomy["data_source"].value_id,
            relationship_direction="UNKNOWN",
            description="Unknown direction",
            effective_date=date(2025, 1, 1),
        ),
    ])
    db_session.commit()

    response = client.get(
        f"/models/{model_a.model_id}/dependencies/lineage",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()

    assert data["model"]["model_id"] == model_a.model_id
    assert len(data.get("upstream", [])) == 1

    node_b = data["upstream"][0]
    assert node_b["model_id"] == model_b.model_id
    assert "upstream_applications" in node_b
    assert "downstream_applications" in node_b

    upstream_apps_b = node_b["upstream_applications"]
    downstream_apps_b = node_b["downstream_applications"]

    assert any(app["application_code"] == "APP-UP-B" for app in upstream_apps_b)
    assert any(app["application_code"] == "APP-DOWN-B" for app in downstream_apps_b)
    assert all(app["relationship_direction"] in ["UPSTREAM", "DOWNSTREAM"] for app in upstream_apps_b + downstream_apps_b)

    # Ensure unknown direction apps are excluded
    assert all(app["application_code"] != "APP-UP-C" for app in upstream_apps_b)

    node_c = node_b["upstream"][0]
    assert node_c["model_id"] == model_c.model_id
    assert any(app["application_code"] == "APP-UP-C" for app in node_c["upstream_applications"])


def test_build_lineage_paths_handles_application_leaves():
    """Ensure path building inserts application nodes at chain ends."""
    lineage_data = {
        "model": {
            "node_type": "model",
            "model_id": 1,
            "model_name": "Model A",
        },
        "upstream": [
            {
                "node_type": "model",
                "model_id": 2,
                "model_name": "Model B",
                "upstream": [],
                "downstream": [],
                "upstream_applications": [
                    {
                        "node_type": "application",
                        "application_id": 10,
                        "application_code": "APP-UP",
                        "application_name": "Upstream App",
                        "relationship_type": "Data Source",
                        "relationship_direction": "UPSTREAM",
                    }
                ],
                "downstream_applications": [],
            }
        ],
        "downstream": [
            {
                "node_type": "model",
                "model_id": 3,
                "model_name": "Model C",
                "upstream": [],
                "downstream": [],
                "upstream_applications": [],
                "downstream_applications": [
                    {
                        "node_type": "application",
                        "application_id": 11,
                        "application_code": "APP-DOWN",
                        "application_name": "Downstream App",
                        "relationship_type": "Output Consumer",
                        "relationship_direction": "DOWNSTREAM",
                    }
                ],
            }
        ],
    }

    paths = build_lineage_paths(lineage_data)
    assert len(paths) == 1
    path = paths[0]

    labels = [(node["node_type"], node.get("model_name") or node.get("application_name")) for node in path]
    assert labels == [
        ("application", "Upstream App"),
        ("model", "Model B"),
        ("model", "Model A"),
        ("model", "Model C"),
        ("application", "Downstream App"),
    ]
