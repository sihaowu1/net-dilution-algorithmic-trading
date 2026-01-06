import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt

def calculate_strategy_returns(df, ticker_name):
    """
    Calculate returns for the trading strategy based on position signals.
    
    Args:
        df: DataFrame with 'position' and 'closing_price' columns
        ticker_name: Name of the ticker for labeling
    
    Returns:
        DataFrame with strategy returns and cumulative returns
    """
    df = df.copy()
    
    # Ensure required columns exist
    if 'closing_price' not in df.columns or 'position' not in df.columns:
        raise ValueError(f"DataFrame must contain 'closing_price' and 'position' columns")
    
    # Filter out rows with missing closing prices
    df = df.dropna(subset=['closing_price']).copy()
    
    if len(df) == 0:
        raise ValueError(f"No valid data rows found for {ticker_name}")
    
    df = df.sort_values('date').reset_index(drop=True)
    
    # Calculate price returns (percent change)
    df['price_return'] = df['closing_price'].pct_change()
    
    # Calculate strategy returns (position * return)
    # Use current period's position to determine current period's return
    # When position = 1 (long): profit when price goes up
    # When position = -1 (short): profit when price goes down
    df['strategy_return'] = df['position'] * df['price_return']
    
    # Calculate cumulative returns
    # Fill NaN values with 0 for the first row (no previous price)
    df['cumulative_market_return'] = (1 + df['price_return'].fillna(0)).cumprod() - 1
    df['cumulative_strategy_return'] = (1 + df['strategy_return'].fillna(0)).cumprod() - 1
    
    return df

def get_sp500_data(start_date, end_date):
    # Ensure dates are in the correct format for yfinance
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # Add one day to end_date to ensure we get data up to that date
    end_date = end_date + pd.Timedelta(days=1)
    
    sp500 = yf.download(
        "^GSPC",
        start=start_date,
        end=end_date,
        progress=False,
        auto_adjust=False,   # set explicitly to silence FutureWarning + keep schema stable
    )

    # Robustly extract Close as a 1-D Series
    close = sp500["Close"]
    if isinstance(close, pd.DataFrame):
        # happens if columns are multi-indexed (e.g., Close has a ticker subcolumn)
        close = close.iloc[:, 0]

    sp500_df = close.rename("sp500_price").reset_index()  # Date -> column
    sp500_df = sp500_df.rename(columns={"Date": "date"})  # yfinance uses "Date"

    sp500_df["sp500_return"] = sp500_df["sp500_price"].pct_change()
    sp500_df["sp500_cumulative_return"] = (1 + sp500_df["sp500_return"].fillna(0)).cumprod() - 1

    return sp500_df

def plot_positions(df, ticker_name):
    """Plot the trading positions over time."""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    df['date_dt'] = pd.to_datetime(df['date'])
    
    # Create a step plot for positions
    ax.step(df['date_dt'], df['position'], where='post', linewidth=2, label='Position')
    ax.fill_between(df['date_dt'], df['position'], step='post', alpha=0.3)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Position', fontsize=12)
    ax.set_title(f'{ticker_name} Trading Positions Over Time', fontsize=14, fontweight='bold')
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(['Short (-1)', 'Neutral (0)', 'Long (+1)'])
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.show()

def plot_performance_comparison(df, sp500_df, ticker_name):
    """Plot cumulative returns comparison with long/short action markers and position over time."""
    fig = plt.figure(figsize=(18, 8))
    
    # Create two subplots side by side
    ax1 = plt.subplot(1, 2, 1)  # Left plot: performance comparison
    ax2 = plt.subplot(1, 2, 2)  # Right plot: position over time
    
    df['date_dt'] = pd.to_datetime(df['date'])
    sp500_df['date_dt'] = pd.to_datetime(sp500_df['date'])
    
    # Ensure we have valid data
    if len(df) == 0:
        raise ValueError(f"No data to plot for {ticker_name}")
    if len(sp500_df) == 0:
        raise ValueError(f"No S&P 500 data available for the date range")
    
    # Plot strategy returns
    ax1.plot(df['date_dt'], df['cumulative_strategy_return'] * 100, 
            linewidth=2.5, label=f'{ticker_name} Strategy', marker='o', markersize=6)
    
    # Plot buy-and-hold returns
    ax1.plot(df['date_dt'], df['cumulative_market_return'] * 100, 
            linewidth=2.5, label=f'{ticker_name} Buy & Hold', marker='s', markersize=6)
    
    # Plot S&P 500 returns
    ax1.plot(sp500_df['date_dt'], sp500_df['sp500_cumulative_return'] * 100, 
            linewidth=2, label='S&P 500', alpha=0.8)
    
    # Detect position changes and mark long/short entries
    df_sorted = df.sort_values('date_dt').reset_index(drop=True)
    df_sorted['position_shift'] = df_sorted['position'].shift(1)
    # Shift cumulative return and date backward by 1 to get the values BEFORE the position change
    df_sorted['cumulative_strategy_return_prev'] = df_sorted['cumulative_strategy_return'].shift(1)
    df_sorted['date_dt_prev'] = df_sorted['date_dt'].shift(1)
    
    # Find entries into long positions (transition to 1)
    long_entries = df_sorted[
        (df_sorted['position'] == 1) & 
        (df_sorted['position_shift'] != 1) &
        (df_sorted['cumulative_strategy_return_prev'].notna())
    ]
    
    # Find entries into short positions (transition to -1)
    short_entries = df_sorted[
        (df_sorted['position'] == -1) & 
        (df_sorted['position_shift'] != -1) &
        (df_sorted['cumulative_strategy_return_prev'].notna())
    ]
    
    # Mark long entries with green upward triangles
    if len(long_entries) > 0:
        ax1.scatter(long_entries['date_dt_prev'], 
                  long_entries['cumulative_strategy_return_prev'] * 100,
                  marker='^', s=150, color='green', zorder=5, 
                  label='Long Entry', edgecolors='darkgreen', linewidths=1.5)
    
    # Mark short entries with red downward triangles
    if len(short_entries) > 0:
        ax1.scatter(short_entries['date_dt_prev'], 
                  short_entries['cumulative_strategy_return_prev'] * 100,
                  marker='v', s=150, color='red', zorder=5, 
                  label='Short Entry', edgecolors='darkred', linewidths=1.5)
    
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return (%)', fontsize=12)
    ax1.set_title(f'{ticker_name} Strategy Performance vs S&P 500', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    
    # Plot position over time with improved styling
    dates = df_sorted['date_dt'].values
    positions = df_sorted['position'].values
    
    # Define colors for each position type (more vibrant and distinct)
    color_long = '#2ecc71'    # Green for long positions
    color_short = '#e74c3c'    # Red for short positions
    
    # Create separate fills for each position type for clean colored regions
    # Fill long positions (1) - from 0 to 1
    long_positions = np.where(positions == 1, positions, 0)
    ax2.fill_between(dates, 0, long_positions, step='post', 
                     alpha=0.5, color=color_long, edgecolor='none')
    
    # Fill short positions (-1) - from -1 to 0
    short_positions = np.where(positions == -1, positions, 0)
    ax2.fill_between(dates, short_positions, 0, step='post', 
                     alpha=0.5, color=color_short, edgecolor='none')
    
    # Draw step line overlay for clarity with better styling
    ax2.step(dates, positions, where='post', 
            linewidth=2.5, color='#2c3e50', alpha=0.9, zorder=10)
    
    # Style the plot
    ax2.set_xlabel('Date', fontsize=12, fontweight='medium')
    ax2.set_ylabel('Position', fontsize=12, fontweight='medium')
    ax2.set_title(f'{ticker_name} Position Over Time', fontsize=14, fontweight='bold', pad=15)
    ax2.set_yticks([-1, 0, 1])
    ax2.set_yticklabels(['Short (-1)', 'Neutral (0)', 'Long (+1)'], fontsize=11)
    
    # Improve grid styling
    ax2.grid(True, alpha=0.2, linestyle='--', linewidth=0.8, axis='y')
    ax2.grid(True, alpha=0.1, linestyle='-', linewidth=0.5, axis='x')
    
    # Add zero line for reference
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.4, linewidth=1.2, zorder=5)
    
    # Improve axis limits for better appearance
    ax2.set_ylim(-1.3, 1.3)
    
    # Format x-axis dates
    ax2.tick_params(axis='x', labelsize=10)
    ax2.tick_params(axis='y', labelsize=10)
    
    plt.tight_layout()
    plt.show()
    return fig