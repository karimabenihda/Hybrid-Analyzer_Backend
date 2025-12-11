from app.hf_model import query


def test_hugging_face(mocker):
    expected_value={
                "labels" : ["Travel","Sports"],
                "scores" : [0.08,0.98]
                    }
    
    mock_query=mocker.patch(__name__+".query",return_value=expected_value)
    
    payload={
        "inputs": "machine learning",
        "parameters": {
            "candidate_labels": ["Travel","Sports"]
        }
    }
    
    response = query(
        payload["inputs"],
        payload["parameters"]["candidate_labels"]
    )   
    assert response ==expected_value
    mock_query.assert_called_once_with(
    payload["inputs"],
    payload["parameters"]["candidate_labels"]
)
