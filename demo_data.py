"""Fixed evaluation data and deliberately synthetic traffic for the demo."""
from __future__ import annotations

RAW_EVAL = """1|failed_payment|critical|Checkout has been failing for all customers since 10am with a generic error. We are losing sales right now.
2|docs_question|low|How do I add a license key to a digital product? Could not find it in the dashboard.
3|billing|high|I was charged twice for the same subscription this month. Please refund one.
4|docs_question|low|Can I use a custom domain for my checkout page?
5|onboarding|medium|We signed up yesterday. How do I connect our Next.js app to the webhooks?
6|tax_compliance|medium|Need a VAT invoice with our EU company ID for last quarter's payments.
7|integration_bug|high|Webhook for subscription.renewed returns 500 from our endpoint. Not sure if the payload is wrong.
8|feature_request|low|Please add UPI Autopay as a payment method.
9|tax_compliance|high|A customer in Germany says tax was applied twice on their invoice.
10|refund|medium|Refund request for order 4421. I cancelled within 24 hours.
11|billing|critical|Our whole customer base cannot log in to the billing portal. It has been down for 30 minutes.
12|docs_question|low|What is the difference between the Standard and Pro plans?
13|docs_question|low|Do you support prorated upgrades on annual plans?
14|failed_payment|high|Payments from India fail with "card declined" but the same card works elsewhere.
15|onboarding|medium|Can someone walk me through setting up tax registration?
16|refund|high|The refund still has not reached my bank account after 10 days.
17|feature_request|low|Please add a Slack channel integration for payment alerts.
18|integration_bug|high|Webhook signature verification keeps failing even though we use the raw request body.
19|billing|medium|Invoices show the wrong company name after I updated my settings.
20|onboarding|low|Just signed up. Is there a sandbox mode for testing?
21|integration_bug|high|Payment succeeded on our side but the license key email never arrived.
22|tax_compliance|medium|Need GST invoice details for Indian customers. Where do I configure them?
23|integration_bug|medium|Checkout page takes about 6 seconds to load for users in Brazil.
24|feature_request|low|Can we export all transactions as CSV for accounting?
25|failed_payment|high|Some customers are charged in USD instead of their local currency.
26|billing|high|A cardholder raised a dispute. What is the process to respond?
27|docs_question|low|What is your refund policy for annual subscriptions?
28|integration_bug|medium|The cancel button on a subscription is greyed out.
29|onboarding|medium|The React SDK example import fails with "module not found".
30|billing|critical|Chargebacks are up 3x since yesterday. Can someone look at our account urgently?
31|feature_request|low|Please allow pausing subscriptions for up to 3 months.
32|tax_compliance|low|Does Dodo handle US state sales tax automatically?
33|billing|high|Test-mode payments are showing up in our live mode reports.
34|onboarding|low|Thanks for the help last week. One more question about metered billing setup.
35|billing|high|Payouts to our bank account have been pending for 5 days.
36|docs_question|low|How do I create a discount code that applies only to annual plans?
37|failed_payment|high|Customers in Southeast Asia get "payment method not supported" at checkout.
38|feature_request|low|Please add Hindi language support on the checkout page.
39|integration_bug|high|Affiliate links stopped tracking commissions this morning.
40|onboarding|medium|We need to migrate 2,000 subscriptions from our old provider. What is the process?
41|refund|medium|Can I issue a partial refund for one line item on an invoice?
42|integration_bug|high|Our webhook endpoint received 40 duplicate events for the same payment.
43|docs_question|low|Where do I find my merchant ID?
44|tax_compliance|high|We got a notice from tax authorities about our VAT filing. We need our Dodo tax reports.
45|billing|high|A customer says they were charged after cancelling. Please check.
46|billing|high|The dashboard shows MRR of zero, but we have 300 active subscribers.
47|feature_request|low|Could you add Polish zloty pricing?
48|account_access|medium|Two-factor login codes are not arriving on my phone.
49|other|low|The product is great. Any tips for scaling checkouts?
50|refund|medium|A refund was requested, but the original payment was made through a different provider."""

EVAL_TICKETS = [tuple(line.split("|", 3)) for line in RAW_EVAL.splitlines()]


def burst_messages(n: int = 15) -> list[str]:
    """Synthetic demo messages: same issue, varied wording for theme grouping."""
    templates = [
        "Synthetic demo: Indian-issued cards are all getting card declined at checkout. Please help!",
        "[Synthetic demo] Our customers in India see 'card declined' when trying checkout.",
        "Synthetic demo traffic: checkout fails for India cards — card declined every time.",
        "hey, synthetic demo here. indian issued visa card says card declined on checkout",
        "Synthetic demo message: card declined errors are blocking Indian cardholders from checkout.",
        "Customers with Indian bank cards cant complete checkout, keeps saying card declined. (synthetic)",
        "SYNTHETIC DEMO: checkout is rejecting every Indian-issued card as declined.",
        "Please investigate: India cards fail at checkout with card declined. Synthetic test ticket.",
        "Synthetic sample — our India-issued credit cards are getting decline msgs during checkout.",
        "checkout issue: card declined for indian cards only!! synthetic demo data",
    ]
    return [templates[i % len(templates)] for i in range(n)]
