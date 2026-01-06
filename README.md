# Net Dilution Algorithmic Trading
## Why look into net dilution in tech companies?

```math
\text{Net Dilution}
=
\frac{\text{Stock-Based Compensation} - \text{Shares Repurchase}}
{\text{Market Cap}}
```

Many companies, especially in tech, are using stock-based compensation (SBC) to attract talent. On the other hand, the company wants to keep shares so that it can decide long-term trajectory. The company can only do this if it is in a good financial position. 

## Hypothesis

So, we hypothesize that a low net dilution means the price will increase, as a low net dilution signals strong financials. A high net dilution therefore means the price will decrease. 

## Backtesting Setup

We will look at tech companies, since they may consider paying employees in significant amounts of SBC to be able to invest cash for growth. 

```math
\text{Expected Net Dilution}
=
\frac{\text{TTM Stock-Based Compensation} - \text{TTM Shares Repurchase}}
{\text{Market Cap at signal date}}
```

The trading signal will be based on a trailing twelve month (TTM) of net dilution. We choose to use a TTM because the market cap is calculated using the point-in-time diluted shares outstanding, which is in 10-K/10-Q fillings, released usually after the company's earnings date. By using the most recent 10-K/10-Q filling and the TTM, we can estimate the net dilution and hence long/short the stock on the earnings date when it is mispriced due to missing number of shares outstanding. 
```math
\text{Market Cap}
=
{\text{Price}} \times {\text{Diluted Shares Outstanding}}
```

Since every company is different, we will use z-score to normalize the net dilution. 
```math
\text{z} = \frac{\text{Expected Net Dilution} - \mu}{\sigma}
```

This strategy will long for a z-score normalized net dilution smaller than 0.05, and short for values larger than 0.25. 

We choose a long threshold of 0.05 as this includes companies that retain stocks that are meaningly non-dilutive. If we choose to exclude this, we would take a long threshold of -0.25, which is net dilution slightly lower than average. 

We choose a short threshold of 0.25 as it is large enough to be considered slightly higher than average (i.e. a company repurchase very little or no any shares). 

Having a deadzone between the long and short threshold may help the strategy avoid a period of uncertainty, which can reduce  transaction costs. 

## Backtesting
Backtesting was done on a few tech stocks that issue a lot of employee SBC. That list is:
* Lyft (LYFT)
* Uber (UBER)
* Snowflake (SNOW)
* Salesforce (CRM)
* Pinterest (PINS)
* Snapchat (SNAP)

Backtests were performed on individual stocks starting from their IPO to the last quarter of 2025. This is more relevant than testing a selected period of a stock as that period may reflect extremes of good and bad financial condition, which will cause our algorithm to only long or only short. This would be irrelevant to showing its effectiveness. 

For each stock, the following data is used:
* Closing prices, from Yahoo Finance
* Point-in-time shares outstanding, from SEC EDGAR
* Cash flow SBC, from SEC EDGAR
* Shares repurchase, from SEC EDGAR

The following steps were applied to the data:
1. Compute TTM for shares repurchase and SBC
2. Compute market cap 
```math
\text{Market Cap}
=
{\text{Price}} \times {\text{Diluted Shares Outstanding}}
```
3. Compute expected net dilution
```math
\text{Expected Net Dilution}
=
\frac{\text{TTM Stock-Based Compensation} - \text{TTM Shares Repurchase}}
{\text{Market Cap}}
```
4. Z-score normalize the expected net dilution. 
5. Generate trading signals.
```math
\text{Position} =
\begin{cases}
\text{Long}, & \text{z-score normalized net dilution} \le 0.05 \\
\text{Short}, & \text{z-score normalized net dilution} \ge 0.25
\end{cases}
```
6. Plot strategy performance vs. single stock buy and hold vs. S&P500 buy and hold. 

## Results
![image](https://raw.githubusercontent.com/sihaowu1/net-dilution-algorithmic-trading/main/trading/charts/LYFT.png)
![image](https://raw.githubusercontent.com/sihaowu1/net-dilution-algorithmic-trading/main/trading/charts/UBER.png)
![image](https://raw.githubusercontent.com/sihaowu1/net-dilution-algorithmic-trading/main/trading/charts/SNOW.png)
![image](https://raw.githubusercontent.com/sihaowu1/net-dilution-algorithmic-trading/main/trading/charts/CRM.png)
![image](https://raw.githubusercontent.com/sihaowu1/net-dilution-algorithmic-trading/main/trading/charts/PINS.png)
![image](https://raw.githubusercontent.com/sihaowu1/net-dilution-algorithmic-trading/main/trading/charts/SNAP.png)

## Analysis
We observe that our strategy trades successfully. This means that the signal is relevant. However, our thresholds may need to be adjusted for better performance. 

We observe that our long threshold works successfully. Salesforce is a large company that aims to retain most shares, so a long threshold of 0.05 includes that objective. 

However, a short threshold is not adequately determined, as a high net dilution can also mean a company issues employee SBC to be able to invest cash for investments and growth. 

Additionally, we see that a deadzone between 0.05 and 0.25 is successful as the algorithm remained neutral when SNOW dropped from 2021 Q4 to 2022 Q1. Similarly, we see the same with Salesforce after its IPO. 

This strategy has a clear disadvantage, which is large changes between quarters. This algorithm only updates every quarter, meaning it would fail if the was a sudden change between quarters. An improvement would be to track the drawdown of each stock and have a neutral position if it reached a maximum value. 

Another improvement to this strategy would be to adjust the thresholds for each stock individually, as Pinterest's position was always long. 