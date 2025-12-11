import app.main as main


def test_mock_gemini(mocker):

    input={
    "text": "machine learning",
    "best_category": "technology"    }

    
    expected_value={
    "summary": "Le machine learning est une branche fondamentale de l'intelligence artificielle qui permet aux systèmes d'apprendre et de s'améliorer à partir de données sans programmation explicite.",
    "tone": "neutre"
  
    }
    
    mock_query=mocker.patch("app.main.generate_gemini_summary",return_value=expected_value)
    response=main.generate_gemini_summary(input["text"],input["best_category"]) 
    assert response==expected_value
    
    mock_query.assert_called_once_with(
    input["text"],input["best_category"]
    )
    
