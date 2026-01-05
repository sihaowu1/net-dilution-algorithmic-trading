import pandas as pd

def compute_ttm_sbc_and_repurchase(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values('date').reset_index(drop=True)

    df['share_repurchase_ttm'] = df['Share Repurchase'].rolling(window=4, min_periods=4).sum()
    df['cash_flow_sbc_ttm'] = df['Cash Flow SBC'].rolling(window=4, min_periods=4).sum()

    return df

def compute_market_cap(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['market_cap'] = df['shares_outstanding'] * df['closing_price']
    return df

def compute_net_dilution(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df['net_dilution'] = (df['cash_flow_sbc_ttm'] - df['share_repurchase_ttm']) / df['market_cap']

    return df

def zscore_normalize_net_dilution(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    mean = df['net_dilution'].mean()
    std = df['net_dilution'].std()
    
    if pd.isna(std) or std == 0:
        df['normalized_net_dilution'] = 0.0
    else:
        df['normalized_net_dilution'] = (df['net_dilution'] - mean) / std
    
    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['position'] = 0

    long_threshold  = 0.05
    short_threshold = 0.25

    df.loc[df['net_dilution'].notna() & (df['normalized_net_dilution'] <= long_threshold), 'position'] = 1
    df.loc[df['net_dilution'].notna() & (df['normalized_net_dilution'] >= short_threshold), 'position'] = -1

    return df