from typesafe_sdk import TypeSafeClient, Noul, Choice, Score
from dotenv import load_dotenv

load_dotenv()

client = TypeSafeClient()

state = "I was charged twice. Refund my money as soon as possible and cancel my order"

questions = {
    "is_it_urgent": Noul(
        instructions="does this customer question needs urgent attention"
    ),
    "ticket_category": Choice(
        instructions="which team should handle this",
        criteria={
            "Payment": "Anything related to payments",
            "Returns": "Anything related to returns, cancellations on orders",
            "Query": "Any query related to products and services",
        },
    ),
    "ticket_severity": Score(
        instructions="How much severe is this query",
        criteria=[
            "low: very basic question",
            "medium: refund asked",
            "high: payment failed, wrongly charged",
            "highest: order not received, app crashed, threat in question",
        ],
    ),
}

results = client.system_one(state=state, questions=questions)

print(results)
