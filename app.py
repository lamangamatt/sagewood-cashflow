"""
Sagewood Event Center - Booking & Cash Flow Tracker
Tracks bookings and predicts cash flow based on payment schedule.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Sagewood Cash Flow",
    page_icon="🏛️",
    layout="wide"
)

# Constants
DEFAULT_WEEKDAY_PRICE = 6500
DEFAULT_WEEKEND_PRICE = 8500
DEPOSIT_AMOUNT = 1000
MONTHLY_FIXED_EXPENSES = 46995  # From proforma

DATA_FILE = Path("bookings.json")

# Helper functions
def load_bookings():
    """Load bookings from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return pd.DataFrame(data) if data else pd.DataFrame()
    return pd.DataFrame()

def save_bookings(df):
    """Save bookings to JSON file."""
    if df.empty:
        data = []
    else:
        data = df.to_dict('records')
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def calculate_payment_schedule(event_date, total_price, booking_date=None):
    """
    Calculate payment schedule for an event.
    - Deposit: $1,000 at booking
    - Halfway payment: 50% of remaining, halfway between booking and event
    - Final payment: 50% of remaining, 30 days before event
    """
    if booking_date is None:
        booking_date = datetime.now().date()
    
    if isinstance(event_date, str):
        event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
    if isinstance(booking_date, str):
        booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
    
    remaining_after_deposit = total_price - DEPOSIT_AMOUNT
    halfway_payment = remaining_after_deposit / 2
    final_payment = remaining_after_deposit / 2
    
    # Calculate dates
    days_until_event = (event_date - booking_date).days
    halfway_date = booking_date + timedelta(days=days_until_event // 2)
    final_date = event_date - timedelta(days=30)
    
    # If halfway date is after final date, adjust
    if halfway_date >= final_date:
        halfway_date = final_date - timedelta(days=7)
    
    # If final date is before today or before booking, adjust
    if final_date <= booking_date:
        final_date = event_date - timedelta(days=7)
        halfway_date = booking_date + timedelta(days=3)
    
    return {
        'deposit': {'amount': DEPOSIT_AMOUNT, 'date': booking_date},
        'halfway': {'amount': halfway_payment, 'date': halfway_date},
        'final': {'amount': final_payment, 'date': final_date},
        'total': total_price
    }

def is_weekend(date):
    """Check if date falls on weekend (Fri, Sat, Sun)."""
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()
    return date.weekday() >= 4  # Friday=4, Saturday=5, Sunday=6

def get_default_price(event_date):
    """Get default price based on day of week."""
    if is_weekend(event_date):
        return DEFAULT_WEEKEND_PRICE
    return DEFAULT_WEEKDAY_PRICE

# Initialize session state
if 'bookings' not in st.session_state:
    st.session_state.bookings = load_bookings()

# Sidebar - Add Booking
with st.sidebar:
    st.header("➕ Add Booking")
    
    with st.form("add_booking"):
        client_name = st.text_input("Client Name*")
        event_date = st.date_input("Event Date*", min_value=datetime.now().date())
        
        # Auto-suggest price based on day
        suggested_price = get_default_price(event_date)
        day_type = "Weekend" if is_weekend(event_date) else "Weekday"
        
        st.caption(f"📅 {day_type} event - suggested ${suggested_price:,}")
        
        price = st.number_input(
            "Total Price ($)*", 
            min_value=0, 
            value=suggested_price,
            step=500,
            help="Adjust for F&F discounts"
        )
        
        is_ff = st.checkbox("Friends & Family discount", value=price < suggested_price)
        
        booking_date = st.date_input(
            "Booking Date", 
            value=datetime.now().date(),
            help="When was the booking made?"
        )
        
        notes = st.text_area("Notes", placeholder="Optional notes...")
        
        deposit_collected = st.checkbox("Deposit collected", value=True)
        
        submitted = st.form_submit_button("Add Booking", use_container_width=True)
        
        if submitted:
            if not client_name:
                st.error("Client name is required")
            else:
                schedule = calculate_payment_schedule(event_date, price, booking_date)
                
                new_booking = {
                    'id': datetime.now().strftime('%Y%m%d%H%M%S'),
                    'client_name': client_name,
                    'event_date': str(event_date),
                    'booking_date': str(booking_date),
                    'total_price': price,
                    'day_type': day_type,
                    'is_ff': is_ff,
                    'notes': notes,
                    'deposit_date': str(schedule['deposit']['date']),
                    'deposit_amount': schedule['deposit']['amount'],
                    'deposit_collected': deposit_collected,
                    'halfway_date': str(schedule['halfway']['date']),
                    'halfway_amount': schedule['halfway']['amount'],
                    'halfway_collected': False,
                    'final_date': str(schedule['final']['date']),
                    'final_amount': schedule['final']['amount'],
                    'final_collected': False,
                }
                
                if st.session_state.bookings.empty:
                    st.session_state.bookings = pd.DataFrame([new_booking])
                else:
                    st.session_state.bookings = pd.concat([
                        st.session_state.bookings, 
                        pd.DataFrame([new_booking])
                    ], ignore_index=True)
                
                save_bookings(st.session_state.bookings)
                st.success(f"✅ Added booking for {client_name}")
                st.rerun()

# Main content
st.title("🏛️ Sagewood Event Center")
st.subheader("Booking & Cash Flow Tracker")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📅 Bookings", "💰 Cash Flow", "⚙️ Settings"])

with tab1:
    # Dashboard
    df = st.session_state.bookings
    
    if df.empty:
        st.info("No bookings yet. Add your first booking using the sidebar.")
    else:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_bookings = len(df)
        total_pipeline = df['total_price'].sum()
        
        # Calculate collected vs pending
        collected = 0
        pending = 0
        
        for _, row in df.iterrows():
            if row.get('deposit_collected', False):
                collected += row['deposit_amount']
            else:
                pending += row['deposit_amount']
            
            if row.get('halfway_collected', False):
                collected += row['halfway_amount']
            else:
                pending += row['halfway_amount']
            
            if row.get('final_collected', False):
                collected += row['final_amount']
            else:
                pending += row['final_amount']
        
        with col1:
            st.metric("Total Bookings", total_bookings)
        
        with col2:
            st.metric("Pipeline Value", f"${total_pipeline:,.0f}")
        
        with col3:
            st.metric("Collected", f"${collected:,.0f}")
        
        with col4:
            st.metric("Pending", f"${pending:,.0f}")
        
        st.divider()
        
        # Upcoming payments
        st.subheader("📬 Upcoming Payments Due")
        
        today = datetime.now().date()
        upcoming = []
        
        for _, row in df.iterrows():
            if not row.get('deposit_collected', False):
                upcoming.append({
                    'Client': row['client_name'],
                    'Type': 'Deposit',
                    'Amount': row['deposit_amount'],
                    'Due Date': row['deposit_date'],
                    'Event Date': row['event_date']
                })
            
            if not row.get('halfway_collected', False):
                upcoming.append({
                    'Client': row['client_name'],
                    'Type': 'Halfway',
                    'Amount': row['halfway_amount'],
                    'Due Date': row['halfway_date'],
                    'Event Date': row['event_date']
                })
            
            if not row.get('final_collected', False):
                upcoming.append({
                    'Client': row['client_name'],
                    'Type': 'Final',
                    'Amount': row['final_amount'],
                    'Due Date': row['final_date'],
                    'Event Date': row['event_date']
                })
        
        if upcoming:
            upcoming_df = pd.DataFrame(upcoming)
            upcoming_df['Due Date'] = pd.to_datetime(upcoming_df['Due Date'])
            upcoming_df = upcoming_df.sort_values('Due Date')
            upcoming_df['Amount'] = upcoming_df['Amount'].apply(lambda x: f"${x:,.0f}")
            upcoming_df['Due Date'] = upcoming_df['Due Date'].dt.strftime('%b %d, %Y')
            st.dataframe(upcoming_df, use_container_width=True, hide_index=True)
        else:
            st.success("All payments collected! 🎉")
        
        # Upcoming events
        st.subheader("📅 Upcoming Events")
        
        df['event_date_dt'] = pd.to_datetime(df['event_date'])
        upcoming_events = df[df['event_date_dt'] >= pd.Timestamp(today)].sort_values('event_date_dt')
        
        if not upcoming_events.empty:
            events_display = upcoming_events[['client_name', 'event_date', 'day_type', 'total_price', 'is_ff']].copy()
            events_display.columns = ['Client', 'Event Date', 'Type', 'Price', 'F&F']
            events_display['Price'] = events_display['Price'].apply(lambda x: f"${x:,.0f}")
            events_display['F&F'] = events_display['F&F'].apply(lambda x: '✓' if x else '')
            st.dataframe(events_display.head(10), use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming events")

with tab2:
    # All Bookings
    st.subheader("All Bookings")
    
    df = st.session_state.bookings
    
    if df.empty:
        st.info("No bookings yet.")
    else:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            show_past = st.checkbox("Show past events", value=False)
        with col2:
            show_ff_only = st.checkbox("Show F&F only", value=False)
        
        display_df = df.copy()
        display_df['event_date_dt'] = pd.to_datetime(display_df['event_date'])
        
        if not show_past:
            display_df = display_df[display_df['event_date_dt'] >= pd.Timestamp(datetime.now().date())]
        
        if show_ff_only:
            display_df = display_df[display_df['is_ff'] == True]
        
        display_df = display_df.sort_values('event_date_dt')
        
        for idx, row in display_df.iterrows():
            with st.expander(f"📅 {row['event_date']} - {row['client_name']} (${row['total_price']:,.0f})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Event Date:** {row['event_date']}")
                    st.write(f"**Day Type:** {row['day_type']}")
                    st.write(f"**Total Price:** ${row['total_price']:,.0f}")
                    if row.get('is_ff'):
                        st.write("**Friends & Family:** Yes ✓")
                    if row.get('notes'):
                        st.write(f"**Notes:** {row['notes']}")
                
                with col2:
                    st.write("**Payment Schedule:**")
                    
                    # Deposit
                    dep_status = "✅" if row.get('deposit_collected') else "⏳"
                    st.write(f"{dep_status} Deposit: ${row['deposit_amount']:,.0f} ({row['deposit_date']})")
                    
                    # Halfway
                    half_status = "✅" if row.get('halfway_collected') else "⏳"
                    st.write(f"{half_status} Halfway: ${row['halfway_amount']:,.0f} ({row['halfway_date']})")
                    
                    # Final
                    final_status = "✅" if row.get('final_collected') else "⏳"
                    st.write(f"{final_status} Final: ${row['final_amount']:,.0f} ({row['final_date']})")
                
                # Payment collection buttons
                st.write("---")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if not row.get('deposit_collected'):
                        if st.button("Mark Deposit Paid", key=f"dep_{row['id']}"):
                            st.session_state.bookings.loc[st.session_state.bookings['id'] == row['id'], 'deposit_collected'] = True
                            save_bookings(st.session_state.bookings)
                            st.rerun()
                
                with col2:
                    if not row.get('halfway_collected'):
                        if st.button("Mark Halfway Paid", key=f"half_{row['id']}"):
                            st.session_state.bookings.loc[st.session_state.bookings['id'] == row['id'], 'halfway_collected'] = True
                            save_bookings(st.session_state.bookings)
                            st.rerun()
                
                with col3:
                    if not row.get('final_collected'):
                        if st.button("Mark Final Paid", key=f"final_{row['id']}"):
                            st.session_state.bookings.loc[st.session_state.bookings['id'] == row['id'], 'final_collected'] = True
                            save_bookings(st.session_state.bookings)
                            st.rerun()
                
                with col4:
                    if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                        st.session_state.bookings = st.session_state.bookings[st.session_state.bookings['id'] != row['id']]
                        save_bookings(st.session_state.bookings)
                        st.rerun()

with tab3:
    # Cash Flow Projection
    st.subheader("Cash Flow Projection")
    
    df = st.session_state.bookings
    
    if df.empty:
        st.info("Add bookings to see cash flow projections.")
    else:
        # Build monthly cash flow
        today = datetime.now().date()
        
        # Get all payment dates
        payments = []
        
        for _, row in df.iterrows():
            # Only include uncollected payments
            if not row.get('deposit_collected', False):
                payments.append({
                    'date': pd.to_datetime(row['deposit_date']),
                    'amount': row['deposit_amount'],
                    'type': 'Deposit'
                })
            
            if not row.get('halfway_collected', False):
                payments.append({
                    'date': pd.to_datetime(row['halfway_date']),
                    'amount': row['halfway_amount'],
                    'type': 'Halfway'
                })
            
            if not row.get('final_collected', False):
                payments.append({
                    'date': pd.to_datetime(row['final_date']),
                    'amount': row['final_amount'],
                    'type': 'Final'
                })
        
        if payments:
            payments_df = pd.DataFrame(payments)
            payments_df['month'] = payments_df['date'].dt.to_period('M')
            
            # Aggregate by month
            monthly_income = payments_df.groupby('month')['amount'].sum().reset_index()
            monthly_income['month_str'] = monthly_income['month'].astype(str)
            
            # Add fixed expenses
            monthly_income['expenses'] = MONTHLY_FIXED_EXPENSES
            monthly_income['net'] = monthly_income['amount'] - monthly_income['expenses']
            
            # Create chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=monthly_income['month_str'],
                y=monthly_income['amount'],
                name='Expected Income',
                marker_color='#22c55e'
            ))
            
            fig.add_trace(go.Bar(
                x=monthly_income['month_str'],
                y=monthly_income['expenses'],
                name='Fixed Expenses',
                marker_color='#ef4444'
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly_income['month_str'],
                y=monthly_income['net'],
                name='Net Cash Flow',
                mode='lines+markers',
                line=dict(color='#3b82f6', width=3)
            ))
            
            fig.update_layout(
                title='Monthly Cash Flow Projection',
                xaxis_title='Month',
                yaxis_title='Amount ($)',
                barmode='group',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show data table
            st.subheader("Monthly Breakdown")
            display_monthly = monthly_income[['month_str', 'amount', 'expenses', 'net']].copy()
            display_monthly.columns = ['Month', 'Expected Income', 'Fixed Expenses', 'Net']
            display_monthly['Expected Income'] = display_monthly['Expected Income'].apply(lambda x: f"${x:,.0f}")
            display_monthly['Fixed Expenses'] = display_monthly['Fixed Expenses'].apply(lambda x: f"${x:,.0f}")
            display_monthly['Net'] = display_monthly['Net'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(display_monthly, use_container_width=True, hide_index=True)
            
            # Warning for negative months
            negative_months = monthly_income[monthly_income['net'] < 0]
            if not negative_months.empty:
                st.warning(f"⚠️ {len(negative_months)} month(s) with projected negative cash flow. Consider accelerating bookings or payment collection.")
        else:
            st.success("All payments have been collected!")

with tab4:
    # Settings
    st.subheader("Settings")
    
    st.write("**Default Pricing**")
    st.info(f"Weekday events: ${DEFAULT_WEEKDAY_PRICE:,}\nWeekend events: ${DEFAULT_WEEKEND_PRICE:,}")
    
    st.write("**Payment Schedule**")
    st.info(f"Deposit: ${DEPOSIT_AMOUNT:,}\nHalfway: 50% of remaining\nFinal (30 days before): 50% of remaining")
    
    st.write("**Monthly Fixed Expenses**")
    st.info(f"${MONTHLY_FIXED_EXPENSES:,}/month (from proforma)")
    
    st.divider()
    
    st.write("**Data Management**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export
        if not st.session_state.bookings.empty:
            csv = st.session_state.bookings.to_csv(index=False)
            st.download_button(
                "📥 Export Bookings (CSV)",
                csv,
                "sagewood_bookings.csv",
                "text/csv",
                use_container_width=True
            )
    
    with col2:
        # Import
        uploaded = st.file_uploader("📤 Import Bookings (CSV)", type=['csv'])
        if uploaded:
            imported_df = pd.read_csv(uploaded)
            st.write(f"Found {len(imported_df)} rows")
            st.write("Columns:", list(imported_df.columns))
            
            # Check for required columns
            required = ['client_name', 'event_date', 'total_price']
            missing = [c for c in required if c not in imported_df.columns]
            
            if missing:
                st.error(f"Missing required columns: {missing}")
                st.info("Required: client_name, event_date, total_price")
                st.info("Optional: booking_date, is_ff, notes")
            else:
                if st.button("Confirm Import"):
                    # Process each row and build full booking records
                    processed = []
                    for _, row in imported_df.iterrows():
                        event_date = str(row['event_date'])
                        price = float(row['total_price'])
                        
                        # Handle optional fields
                        booking_date = str(row.get('booking_date', datetime.now().date()))
                        if pd.isna(row.get('booking_date')):
                            booking_date = str(datetime.now().date())
                        
                        is_ff_val = row.get('is_ff', False)
                        if isinstance(is_ff_val, str):
                            is_ff = is_ff_val.lower() in ['true', 'yes', '1', 'y']
                        else:
                            is_ff = bool(is_ff_val) if not pd.isna(is_ff_val) else False
                        
                        notes = str(row.get('notes', '')) if not pd.isna(row.get('notes')) else ''
                        
                        # Calculate payment schedule
                        schedule = calculate_payment_schedule(event_date, price, booking_date)
                        day_type = "Weekend" if is_weekend(event_date) else "Weekday"
                        
                        processed.append({
                            'id': datetime.now().strftime('%Y%m%d%H%M%S') + str(len(processed)),
                            'client_name': str(row['client_name']),
                            'event_date': event_date,
                            'booking_date': booking_date,
                            'total_price': price,
                            'day_type': day_type,
                            'is_ff': is_ff,
                            'notes': notes,
                            'deposit_date': str(schedule['deposit']['date']),
                            'deposit_amount': schedule['deposit']['amount'],
                            'deposit_collected': False,
                            'halfway_date': str(schedule['halfway']['date']),
                            'halfway_amount': schedule['halfway']['amount'],
                            'halfway_collected': False,
                            'final_date': str(schedule['final']['date']),
                            'final_amount': schedule['final']['amount'],
                            'final_collected': False,
                        })
                    
                    st.session_state.bookings = pd.DataFrame(processed)
                    save_bookings(st.session_state.bookings)
                    st.success(f"Imported {len(processed)} bookings!")
                    st.rerun()
    
    st.divider()
    
    # Clear all
    if st.button("🗑️ Clear All Bookings", type="secondary"):
        if st.checkbox("I understand this will delete all data"):
            st.session_state.bookings = pd.DataFrame()
            save_bookings(st.session_state.bookings)
            st.success("All bookings cleared")
            st.rerun()

# Footer
st.divider()
st.caption("Sagewood Event Center - Cash Flow Tracker v1.0")
