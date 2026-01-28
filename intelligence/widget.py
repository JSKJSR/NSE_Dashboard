"""
Market Intelligence Streamlit Widget
MVP Version - Display prioritized market events
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

from intelligence.news_fetcher import NewsFetcher
from intelligence.classifier import classify_news, detect_critical_events
from intelligence.storage import get_storage
from intelligence.config import PRIORITY_LEVELS, EVENT_CATEGORIES


def render_intelligence_widget(container=None):
    """
    Render the market intelligence widget.

    Args:
        container: Optional Streamlit container to render in
    """
    target = container or st

    with target:
        st.markdown("### 📡 Market Intelligence")

        # Refresh button and last update time
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Refresh", key="intel_refresh"):
                _fetch_and_process_news()
                st.rerun()

        with col2:
            if "intel_last_update" in st.session_state:
                st.caption(f"Last updated: {st.session_state.intel_last_update}")

        # Auto-refresh on first load
        if "intel_initialized" not in st.session_state:
            _fetch_and_process_news()
            st.session_state.intel_initialized = True

        # Get events from storage
        storage = get_storage()
        events = storage.get_recent_events(limit=20, hours=24)

        if not events:
            st.info("No market events in the last 24 hours. Click refresh to fetch latest news.")
            return

        # Display critical alerts first
        critical_events = [e for e in events if e["priority_level"] == "CRITICAL"]
        if critical_events:
            _render_critical_alerts(critical_events)

        # Display event summary
        _render_event_summary(events)

        # Display event feed
        _render_event_feed(events)


def _fetch_and_process_news():
    """Fetch news, classify, and store events."""
    try:
        # Fetch news
        fetcher = NewsFetcher()
        news_items = fetcher.fetch_all()

        if news_items:
            # Classify events
            classified = classify_news(news_items)

            # Store events
            storage = get_storage()
            new_count = storage.save_events(classified)

            # Cleanup old events
            storage.cleanup_old_events()

            st.session_state.intel_last_update = datetime.now().strftime("%H:%M:%S")
            st.session_state.intel_new_count = new_count

    except Exception as e:
        st.error(f"Error fetching news: {e}")


def _render_critical_alerts(events: List[Dict]):
    """Render critical alert banner."""
    st.markdown("""
    <style>
    .critical-alert {
        background: linear-gradient(90deg, #ff4444 0%, #cc0000 100%);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    </style>
    """, unsafe_allow_html=True)

    for event in events[:3]:  # Show max 3 critical alerts
        st.markdown(f"""
        <div class="critical-alert">
            <strong>🔴 CRITICAL:</strong> {event['headline'][:100]}...
            <br><small>{event['source']} | {event['category']}</small>
        </div>
        """, unsafe_allow_html=True)


def _render_event_summary(events: List[Dict]):
    """Render event summary metrics."""
    # Count by priority
    priority_counts = {}
    for level in PRIORITY_LEVELS:
        priority_counts[level] = sum(1 for e in events if e["priority_level"] == level)

    # Count by category
    category_counts = {}
    for cat in EVENT_CATEGORIES:
        category_counts[cat] = sum(1 for e in events if e["category"] == cat)

    # Display summary
    cols = st.columns(4)
    with cols[0]:
        st.metric("Critical", priority_counts.get("CRITICAL", 0))
    with cols[1]:
        st.metric("High", priority_counts.get("HIGH", 0))
    with cols[2]:
        st.metric("Medium", priority_counts.get("MEDIUM", 0))
    with cols[3]:
        st.metric("Total", len(events))


def _render_event_feed(events: List[Dict]):
    """Render the scrollable event feed."""
    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        category_filter = st.selectbox(
            "Category",
            ["All"] + list(EVENT_CATEGORIES.keys()),
            key="intel_category_filter"
        )
    with col2:
        priority_filter = st.selectbox(
            "Min Priority",
            ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
            key="intel_priority_filter"
        )

    # Apply filters
    filtered_events = events
    if category_filter != "All":
        filtered_events = [e for e in filtered_events if e["category"] == category_filter]
    if priority_filter != "All":
        min_priority = PRIORITY_LEVELS.get(priority_filter, {}).get("min", 0)
        filtered_events = [e for e in filtered_events if e["priority"] >= min_priority]

    # Render events
    st.markdown("---")

    if not filtered_events:
        st.info("No events match the selected filters.")
        return

    for event in filtered_events:
        _render_event_card(event)


def _render_event_card(event: Dict):
    """Render a single event card."""
    priority_color = event.get("color", "#808080")
    emoji = event.get("emoji", "⚪")
    sentiment = event.get("sentiment", {})
    sentiment_score = sentiment.get("score", 0)

    # Sentiment indicator
    if sentiment_score > 0.1:
        sent_indicator = "🟢"
        sent_text = "Bullish"
    elif sentiment_score < -0.1:
        sent_indicator = "🔴"
        sent_text = "Bearish"
    else:
        sent_indicator = "⚪"
        sent_text = "Neutral"

    # Format timestamp
    timestamp = event.get("timestamp", "")
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = timestamp.strftime("%H:%M")
        except:
            time_str = str(timestamp)[:5]
    else:
        time_str = timestamp.strftime("%H:%M") if timestamp else ""

    # Render card
    st.markdown(f"""
    <div style="
        border-left: 4px solid {priority_color};
        padding: 8px 12px;
        margin-bottom: 8px;
        background: rgba(0,0,0,0.05);
        border-radius: 0 5px 5px 0;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.8em; color: #666;">
                {emoji} {event['priority_level']} | {event['category']} | {event['source']}
            </span>
            <span style="font-size: 0.75em; color: #888;">{time_str}</span>
        </div>
        <div style="margin: 5px 0; font-weight: 500;">
            {event['headline'][:120]}{'...' if len(event.get('headline', '')) > 120 else ''}
        </div>
        <div style="font-size: 0.8em; color: #666;">
            Sentiment: {sent_indicator} {sent_text} ({sentiment_score:+.2f})
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Link to source
    if event.get("url"):
        st.markdown(f"[Read more →]({event['url']})", unsafe_allow_html=True)


def render_compact_widget():
    """
    Render a compact version of the widget for sidebar or small spaces.
    """
    storage = get_storage()
    events = storage.get_recent_events(limit=5, hours=12)

    st.markdown("#### 📡 Market Intel")

    if not events:
        st.caption("No recent events")
        return

    # Show critical count
    critical_count = sum(1 for e in events if e["priority_level"] == "CRITICAL")
    if critical_count > 0:
        st.markdown(f"🔴 **{critical_count} Critical Alert(s)**")

    # Show top events
    for event in events[:5]:
        emoji = event.get("emoji", "⚪")
        st.markdown(f"{emoji} {event['headline'][:60]}...")

    if st.button("View All", key="view_all_intel"):
        st.session_state.show_intel_page = True


def render_intelligence_page():
    """
    Render a full page for market intelligence.
    Use this as a separate page in your Streamlit app.
    """
    st.title("📡 Market Intelligence Dashboard")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Live Feed", "Critical Events", "Analytics"])

    with tab1:
        render_intelligence_widget()

    with tab2:
        _render_critical_events_tab()

    with tab3:
        _render_analytics_tab()


def _render_critical_events_tab():
    """Render critical events analysis."""
    storage = get_storage()
    events = storage.get_critical_events(hours=24)

    st.markdown("### 🔴 Critical Events (Last 24 Hours)")

    if not events:
        st.success("No critical events detected in the last 24 hours.")
        return

    for event in events:
        with st.expander(f"{event['headline'][:80]}...", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Category:** {event['category']}")
                st.write(f"**Source:** {event['source']}")
                st.write(f"**Priority:** {event['priority']:.1f}")
            with col2:
                sentiment = event.get("sentiment", {})
                st.write(f"**Sentiment:** {sentiment.get('label', 'N/A')}")
                st.write(f"**Score:** {sentiment.get('score', 0):+.2f}")

            if event.get("summary"):
                st.write(f"**Summary:** {event['summary'][:300]}...")

            if event.get("url"):
                st.markdown(f"[Read Full Article]({event['url']})")


def _render_analytics_tab():
    """Render analytics and statistics."""
    storage = get_storage()
    counts = storage.get_event_counts(hours=24)

    st.markdown("### 📊 Event Analytics (Last 24 Hours)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### By Category")
        if counts["by_category"]:
            for cat, count in sorted(counts["by_category"].items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{cat}:** {count}")
        else:
            st.write("No data available")

    with col2:
        st.markdown("#### By Priority")
        if counts["by_priority"]:
            for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                count = counts["by_priority"].get(level, 0)
                emoji = PRIORITY_LEVELS.get(level, {}).get("emoji", "⚪")
                st.write(f"- {emoji} **{level}:** {count}")
        else:
            st.write("No data available")

    st.metric("Total Events", counts.get("total", 0))
