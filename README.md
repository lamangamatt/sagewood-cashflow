# Sagewood Event Center - Cash Flow Tracker

Interactive booking and cash flow prediction tool for event venues.

## Features

- **Booking Management** - Add bookings with client name, event date, and pricing
- **Payment Schedule** - Auto-calculates payment dates based on:
  - $1,000 deposit at booking
  - 50% of remaining halfway to event
  - 50% of remaining 30 days before event
- **Cash Flow Projection** - Monthly income vs expenses chart
- **Dashboard** - Upcoming payments, events, and collection status
- **F&F Discounts** - Track friends & family discounted bookings

## Default Pricing

- Weekday events: $6,500
- Weekend events (Fri-Sun): $8,500
- Custom pricing available for each booking

## Usage

1. Add bookings via the sidebar
2. Mark payments as collected when received
3. View cash flow projections in the Cash Flow tab
4. Export/import data via Settings

## Deployment

Deployed on Streamlit Cloud. Data persists via JSON file storage.
