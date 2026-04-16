import pytest
from src.embeddings import get_embedding, get_embeddings


def test_single_embedding_returns_correct_dimension():
    vec = get_embedding("government scheme for farmers")
    assert len(vec) == 384
    assert isinstance(vec[0], float)


def test_hindi_embedding_returns_correct_dimension():
    vec = get_embedding("किसानों के लिए सरकारी योजना")
    assert len(vec) == 384


def test_batch_embeddings():
    texts = ["farmer income support", "child fever treatment"]
    vecs = get_embeddings(texts)
    assert len(vecs) == 2
    assert len(vecs[0]) == 384


def test_cross_lingual_similarity():
    """Hindi and English descriptions of the same concept should be similar."""
    en = get_embedding("income support scheme for small farmers")
    hi = get_embedding("छोटे किसानों के लिए आय सहायता योजना")
    dot = sum(a * b for a, b in zip(en, hi))
    assert dot > 0.5, f"Cross-lingual similarity too low: {dot}"
