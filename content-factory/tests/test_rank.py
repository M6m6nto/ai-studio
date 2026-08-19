from engines.scout.rank import Post, engagement_rate, rank_topics, suggest_codeword, viral_ratio


def make_post(**kw) -> Post:
    base = dict(post_id="p1", account="acc", title="Тема", url="https://example.com")
    base.update(kw)
    return Post(**base)


def test_engagement_rate_zero_views_is_zero():
    assert engagement_rate(make_post(views=0, likes=100)) == 0.0


def test_engagement_rate_formula():
    p = make_post(likes=100, comments=10, saves=5, views=1000)
    # (100 + 3*10 + 5*5) / 1000 = 155/1000
    assert engagement_rate(p) == 0.155


def test_viral_ratio_zero_followers_is_zero():
    assert viral_ratio(make_post(followers=0, views=1000)) == 0.0


def test_viral_ratio_formula():
    assert viral_ratio(make_post(views=5000, followers=1000)) == 5.0


def test_suggest_codeword_skips_stopwords_and_short_words():
    assert suggest_codeword("Как убрать шум в комнате") == "УБРАТЬ"
    assert suggest_codeword("GitHub в промпт") == "GITHUB"


def test_suggest_codeword_empty_title_fallback():
    assert suggest_codeword("!!!") == "TEMA"


def test_rank_topics_sorts_by_er_desc():
    low = make_post(post_id="low", title="Низкий ER пост", likes=1, comments=0, saves=0, views=1000)
    high = make_post(post_id="high", title="Высокий ER пост", likes=500, comments=50, saves=50, views=1000)
    ranked = rank_topics([low, high], taken_codewords=set(), top=4)
    assert [c["post_id"] for c in ranked] == ["high", "low"]


def test_rank_topics_filters_taken_codeword():
    p = make_post(title="Секретный стек технологий")  # codeword -> СЕКРЕТНЫЙ
    ranked = rank_topics([p], taken_codewords={"СЕКРЕТНЫЙ"}, top=4)
    assert ranked == []


def test_rank_topics_respects_top_limit():
    posts = [make_post(post_id=str(i), title=f"Тема номер {i}", likes=i, views=1000) for i in range(10)]
    ranked = rank_topics(posts, taken_codewords=set(), top=3)
    assert len(ranked) == 3
