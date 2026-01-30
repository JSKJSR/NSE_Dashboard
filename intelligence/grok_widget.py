"""
Grok X Intelligence Widget
Fetches trending financial/geopolitical news from X using xAI's Grok API
"""

import os
import streamlit as st
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Cache duration in seconds
CACHE_DURATION = 300  # 5 minutes


def get_grok_client():
    """Initialize xAI Grok client."""
    try:
        from xai_sdk import Client
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            return None
        return Client(api_key=api_key)
    except ImportError:
        logger.warning("xai-sdk not installed. Install with: pip install xai-sdk")
        return None
    except Exception as e:
        logger.error(f"Error initializing Grok client: {e}")
        return None


def fetch_trending_news(client) -> str:
    """
    Fetch trending financial/geopolitical news from X using Grok.

    Returns:
        Formatted summary of top 5 trending news items
    """
    try:
        from xai_sdk.chat import user, system
        from xai_sdk.tools import x_search

        # Create chat with x_search tool enabled
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[x_search()],
        )

        # System prompt for financial news summarization
        chat.append(system(
            "You are a financial news analyst. Provide concise, actionable summaries "
            "focused on market-moving events. Format each item with a brief headline "
            "and 1-sentence impact analysis. Focus on: monetary policy, geopolitical "
            "events, major market moves, and institutional activity."
        ))

        # Query for trending financial news
        chat.append(user(
            "Summarize the top 5 financial and geopolitical news items currently "
            "trending on X (Twitter). Focus on news that could impact stock markets, "
            "especially Indian markets (NIFTY). Include any breaking news about: "
            "central bank policies, US-India relations, major market moves, "
            "FII/DII activity, or significant corporate announcements."
        ))

        # Get response
        response = chat.sample()
        return response.content if hasattr(response, 'content') else str(response)

    except Exception as e:
        logger.error(f"Error fetching trending news: {e}")
        return None


def render_grok_widget():
    """
    Render the Grok X Intelligence widget.
    Shows trending financial/geopolitical news from X.
    """
    st.markdown("### X Trending News")

    # Check for API key
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        st.info("Set XAI_API_KEY to enable X trending news")
        st.caption("Get your API key from [x.ai/api](https://x.ai/api)")
        return

    # Initialize session state for caching
    if "grok_news_cache" not in st.session_state:
        st.session_state.grok_news_cache = None
        st.session_state.grok_news_timestamp = None

    # Check cache validity
    cache_valid = False
    if st.session_state.grok_news_timestamp:
        age = (datetime.now() - st.session_state.grok_news_timestamp).total_seconds()
        cache_valid = age < CACHE_DURATION

    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        refresh = st.button("Refresh", key="grok_refresh", use_container_width=True)

    # Fetch news if cache invalid or refresh requested
    if not cache_valid or refresh:
        with st.spinner("Fetching X trends..."):
            client = get_grok_client()
            if client:
                news = fetch_trending_news(client)
                if news:
                    st.session_state.grok_news_cache = news
                    st.session_state.grok_news_timestamp = datetime.now()
                else:
                    st.warning("Could not fetch trending news")
                    return
            else:
                st.error("Grok client initialization failed")
                return

    # Display cached news
    if st.session_state.grok_news_cache:
        st.markdown(st.session_state.grok_news_cache)

        # Show last update time
        if st.session_state.grok_news_timestamp:
            time_str = st.session_state.grok_news_timestamp.strftime("%H:%M:%S")
            st.caption(f"Last updated: {time_str}")
    else:
        st.caption("Click Refresh to fetch trending news from X")


def render_compact_grok_widget():
    """
    Render a compact version of the Grok widget for the sidebar.
    """
    st.markdown("#### X Trends")

    # Check for API key
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        st.caption("Set XAI_API_KEY for X trends")
        return

    # Initialize session state
    if "grok_news_cache" not in st.session_state:
        st.session_state.grok_news_cache = None
        st.session_state.grok_news_timestamp = None

    # Check cache
    cache_valid = False
    if st.session_state.grok_news_timestamp:
        age = (datetime.now() - st.session_state.grok_news_timestamp).total_seconds()
        cache_valid = age < CACHE_DURATION

    # Refresh button
    if st.button("Fetch X Trends", key="grok_compact_refresh", use_container_width=True):
        with st.spinner("..."):
            client = get_grok_client()
            if client:
                news = fetch_trending_news(client)
                if news:
                    st.session_state.grok_news_cache = news
                    st.session_state.grok_news_timestamp = datetime.now()
                    st.rerun()

    # Display news
    if st.session_state.grok_news_cache and cache_valid:
        # Truncate for compact view
        news = st.session_state.grok_news_cache
        st.markdown(news, unsafe_allow_html=False)

        if st.session_state.grok_news_timestamp:
            time_str = st.session_state.grok_news_timestamp.strftime("%H:%M")
            st.caption(f"Updated: {time_str}")
    elif not cache_valid:
        st.caption("Click above to fetch X trends")
