from datetime import datetime, timezone
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import PromptTemplate
from quality_agent.logger import setup_logger

logger = setup_logger(__name__)

schedule_prompt = (
    """You are an AI agent responsible for extracting sales and transactions related data from given reciept/bill image. Your task is to take the user's request and extract the
       ### Fields Description
        - `saleDate` (Python date time object): The date and time of the sale.
        - `items` (Array of Objects): A list of items purchased in the sale. Each item object contains:
            - `name` (String): The name of the item.
            - `tags` (Array of Strings): Tags describing the item's category or use (e.g., "office", "school").
            - `price` (Number): The price of one/single item (in USD $).
            - `quantity` (Integer): The quantity of the item purchased.
            - `storeLocation` (String): The location of the store where the sale occurred (e.g., "Denver").
        - `customer` (Object): Information about the customer who made the purchase. The `customer` object includes:
            - `gender` (String): The gender of the customer (e.g., "M", "F").
            - `age` (Integer): The age of the customer.
            - `email` (String): The email address of the customer.
            - `satisfaction` (Integer): A satisfaction rating provided by the customer, ranging from 1 (low) to 5 (high).
        - `couponUsed` (Boolean): Indicates whether a coupon was used during the purchase (True/False).
        - `purchaseMethod` (String): The method used to complete the purchase (e.g., "Online", "In store", "Phone").

        If any of the above fields related data doesnt exist in the given receipt/bill image, then fill the missing information with empty string.
    The user's request is:{question}
    Today's date is {present_date}
    """
)

def get_schedule_prompt():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", schedule_prompt),
            MessagesPlaceholder(variable_name="question"),
        ]
    ).partial(present_date=datetime.now(tz=timezone.utc))
    return prompt


