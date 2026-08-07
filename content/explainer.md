# ETF mechanics, in plain English

These are my notes. I wrote them while building the simulator, partly because
writing something down is the only way I find out whether I actually understand
it.

## There are two markets, and that's the whole trick

Nearly all ETF trading happens in the secondary market: investors buying and
selling existing ETF shares with each other on an exchange. The fund itself is
not involved and does not know or care.

The primary market is a different world. Only Authorised Participants can
transact there, they need a signed agreement with the issuer, and they can only
deal in large blocks called creation units, usually tens of thousands of ETF
shares at a time. An AP hands the fund a basket of the underlying stocks and
receives new ETF shares, or hands back ETF shares and receives the basket.

This is why an ETF behaves so differently from a mutual fund. If I sell a mutual
fund, the manager may have to sell holdings to pay me, and every remaining
investor eats the transaction cost and any realised gains. If I sell an ETF, I
sell to another investor. The fund's portfolio doesn't move.

## NAV, iNAV, and the price on the screen are three different numbers

NAV is the official valuation, struck once a day at the close: assets minus
liabilities, divided by shares outstanding.

iNAV is the intraday estimate, published roughly every 15 seconds by repricing
the fund's disclosed basket with live prices. Estimate is the operative word.
When a European investor buys an S&P 500 UCITS ETF at 9am Dublin time, the US
market is shut and the iNAV is quoting last night's closing prices. It is stale
by design and everyone knows it.

The market price is just whatever the order book says.

The premium or discount is (price minus NAV) over NAV. It exists because
supply and demand in the secondary market move the price around without any
reference to what the fund holds.

## What actually closes the gap

Say the ETF is trading at a 0.60% premium and the AP's all-in cost of doing a
creation is 0.25%. That cost is not one thing: it's basket execution, the
issuer's creation-unit fee, and the risk carried while the trade is on.

The AP buys the underlying basket and shorts the ETF at the same time, so it's
hedged from the first second. It delivers the basket to the fund in-kind, gets
new ETF shares back at NAV, and uses those to close the short. It keeps about
0.35% and never takes a directional position.

The part that took me a while to see is that the trade and the correction are
the same event. The AP isn't fixing the premium as a public service. It sells
new ETF shares because that's how it captures the spread, and selling new shares
is what adds supply and pushes the price down. A discount runs in reverse: buy
the cheap ETF shares, redeem them for the basket, sell the basket, and supply
shrinks on the way through.

So the gap sits inside a band whose half-width is roughly the AP's cost. Cheap
basket to trade, tight band, premiums that vanish in seconds. Expensive basket,
high-yield credit or frontier equity or anything that doesn't trade all day, and
the band is wide enough that half a percent can sit there for hours. That's not
the fund being broken. That's the fund telling you what its holdings cost to
transact right now, which during a stressed market is arguably more useful than
a stale NAV.

## In-kind versus cash

In-kind means securities move, not money. The AP delivers or receives the actual
stocks, so the fund's own trading costs stay near zero and the cost sits with
the AP, whose client caused the flow in the first place. In the US there's a tax
angle too: handing out low-cost-basis stock on redemption disposes of it without
realising a gain.

Cash creation is the fallback where delivery is impractical. Bonds that settle
awkwardly, markets with foreign-ownership registration, that sort of thing. The
AP delivers cash plus a fee meant to cover the fund's estimated execution cost.
UCITS ETFs often run a hybrid: mostly in-kind with a cash residual.

## Why Ireland

Most European UCITS ETF assets are domiciled in Ireland, and the main reason is
tax rather than anything glamorous.

Under the US-Ireland treaty, an Irish-domiciled fund pays 15% withholding tax on
US dividends. A Luxembourg fund pays 30%. On an S&P 500 fund yielding a bit over
1%, that difference is worth somewhere around 15 to 20 basis points a year,
which on a lot of these products is larger than the entire management fee. It is
genuinely strange that the single biggest driver of long-run performance in a
low-cost index fund is a tax treaty.

The rest stacks up on top. Ireland charges no withholding on distributions to
non-resident investors. Luxembourg levies a small subscription tax that Ireland
doesn't. The ICAV is a corporate vehicle built specifically for funds. And
Dublin has thirty years of administrators, custodians, auditors and fund lawyers
who do nothing else.

Worth noting for anyone wondering why we can't just buy the US-listed original:
US ETFs don't publish PRIIPs KIDs, so EU brokers can't sell them to retail
clients. The UCITS version isn't a preference, it's the only door.

## Tracking difference and tracking error measure different things

Tracking difference is the signed gap between fund return and index return over
a period. Fees drag it down, withholding tax drags it down, securities-lending
revenue adds a little back, and sampling moves it either way. It answers the
question of what holding the fund cost me.

Tracking error is the standard deviation of the daily return differences. It
answers how tightly the fund hugs the index day to day.

They come apart easily. A fund can lag by exactly its fee every single year,
which is a large tracking difference and almost no tracking error. Another can
wobble either side of zero and average out, which is the opposite. I'd take the
first one.

Premium and discount is a third thing entirely, and people mix it in constantly.
It's about market price against NAV, which is secondary-market plumbing. It says
nothing about how well the portfolio is managed.

## "Flows" are just AP activity

Reported ETF flows are net creations minus redemptions, which means they are a
record of what APs did in the primary market. Headlines treat this as investor
sentiment, and sometimes it is. But a redemption can just as easily mean the ETF
drifted to a discount and an AP arbitraged it, or that a market maker trimmed
inventory it had been sitting on. The end investors may not have gone anywhere.

## The short version

- Investors trade with each other; only APs trade with the fund.
- The AP's cost of trading sets the width of the band the premium lives in.
- The arbitrage trade and the price correction are the same transaction.
- In-kind creation keeps trading costs and tax outside the fund.
- Ireland's 15% US dividend withholding beats Luxembourg's 30%, worth more than
  the fee on an S&P 500 tracker.
- Tracking difference is the toll, tracking error is the wobble, and
  premium/discount is neither.

---

Written as part of a learning project. None of it is investment advice.
