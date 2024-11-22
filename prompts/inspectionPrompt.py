from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import PromptTemplate
from datetime import datetime
from bson import json_util
from quality_agent.logger import setup_logger
from langchain_core.prompts import MessagesPlaceholder

logger = setup_logger(__name__)


example_query1 = "List all customers with accounts that have a credit limit above $20,000. Retrieve their names, account IDs, and credit limits"
example_query2 = "Find all customers who have made more than 5 transactions and list their names and transaction counts."
example_query3 = "Retrieve all customers with 'Gold' membership who have made transactions above $3,000. Display their names, account IDs, and transaction details"
example_query4 = "Find the top 10 transactions with the highest amounts, including the account ID, transaction date, and total amount."

example_query1_output = """
[
    {
        "$lookup": {
            "from": "accounts",
            "localField": "account_ids",
            "foreignField": "account_id",
            "as": "customer_accounts"
        }
    },
    {
        "$unwind": "$customer_accounts"
    },
    {
        "$match": {
            "customer_accounts.limit": { "$gt": 20000 }
        }
    },
    {
        "$project": {
            "name": 1,
            "customer_accounts.account_id": 1,
            "customer_accounts.limit": 1,
            "_id": 0
        }
    }
]

"""

example_query2_output = """
[
    {
        "$lookup": {
            "from": "transactions",
            "localField": "account_ids",
            "foreignField": "account_id",
            "as": "customer_transactions"
        }
    },
    {
        "$addFields": {
            "transaction_count": { "$size": "$customer_transactions" }
        }
    },
    {
        "$match": {
            "transaction_count": { "$gt": 5 }
        }
    },
    {
        "$project": {
            "name": 1,
            "transaction_count": 1,
            "_id": 0
        }
    }
]
"""

example_query3_output = """
[
    {
        "$match": {
            "tier_and_details.tier": "Gold"
        }
    },
    {
        "$lookup": {
            "from": "accounts",
            "localField": "account_ids",
            "foreignField": "account_id",
            "as": "customer_accounts"
        }
    },
    {
        "$unwind": "$customer_accounts"
    },
    {
        "$lookup": {
            "from": "transactions",
            "localField": "customer_accounts.account_id",
            "foreignField": "account_id",
            "as": "customer_transactions"
        }
    },
    {
        "$unwind": "$customer_transactions"
    },
    {
        "$match": {
            "customer_transactions.amount": { "$gt": 3000 }
        }
    },
    {
        "$project": {
            "name": 1,
            "customer_accounts.account_id": 1,
            "customer_transactions": 1,
            "_id": 0
        }
    }
]

"""

example_query4_output = """
[
    {
        "$sort": {
            "amount": -1
        }
    },
    {
        "$limit": 10
    },
    {
        "$project": {
            "account_id": 1,
            "date": 1,
            "amount": 1,
            "_id": 0
        }
    }
]
"""

query_examples = {'example_query1': example_query1, 'example_query_output1': example_query1_output, 'example_query2': example_query2, 'example_query_output2': example_query2_output, 'example_query3': example_query3, 'example_query_output3': example_query3_output, 'example_query4': example_query4, 'example_query_output4': example_query4_output}

sample_analytics_mongodb_prompt = """
You are a very intelligent AI assistant who is an expert in identifying relevant questions from the user and converting them into NoSQL MongoDB aggregation pipeline queries.
Please use the **provided schemas** for the collections to write the MongoDB queries and avoid using any other assumptions/ assume filed names from user query.

You are working with the `sample_analytics` database, which contains the following collections:

1. **accounts**

2. **customers**

3. **transactions**

**Relationships between the collections:**

- **customers → accounts**: Customers are associated with accounts through `account_id`. Each customer may have one or more accounts.
- **accounts → transactions**: Transactions are linked to accounts via `account_id`. Each transaction belongs to a specific account.
- **customers → transactions (indirect)**: Customers and transactions are connected through `account_id` present in both `accounts` and `transactions`. This relationship allows access to customer transactions by first finding their accounts.

Schemas:
The following MongoDB collection schemas contain various details based on the input schemas provided. Each schema describes the structure of the data, properties, and relationships between fields.
Here is a breakdown of the schemas:

{collection_schemas}

Examples for context:
    Input1: {example_query1}
    Output1: {example_query_output1}

    Input2: {example_query2}
    Output2: {example_query_output2}

    Input3: {example_query3}
    Output3: {example_query_output3}

    Input4: {example_query4}
    Output4: {example_query_output4}

Input: {user_question}
Today's date is {present_date}


Important Note:
1. All dates must be in ISODate BSON type and do not use '$date' in queries.
2. Only return the query formatted for use in the aggregation pipeline. Do not include any other text or explanations.
3. Always exclude or project redundant fields in the query.
4. Handle Empyt results, arrays and null values properly so that pipeline query does not fail.
5. Double check the syntax and structure of the query before submitting.
6. You should strictly follow the provided schemas for the collections and avoid making any assumptions or using assumed field names.


The response must be a JSON object containing two main fields. The first field, named base_collection, should be a string specifying the name of the collection on which the aggregation pipeline will be executed. The second field, called pipeline, should be an array that holds the stages of the aggregation pipeline. Each element within this array should represent a stage of the pipeline as a JSON object, where each object outlines the specific details of that stage. This structure ensures clarity and consistent formatting of the generated query and its execution context.
The response should not have back ticks, new lines, or any other formatting elements. Only the JSON object with the base_collection and pipeline fields should be returned.

"""


fetch_collections_prompt = """
You are working with the `sample_analytics` database, which contains the following collections:

1. **accounts**: Contains details on customer accounts, including account IDs, credit limits, and products associated with each account.

2. **customers**: Stores customer information such as usernames, names, addresses, birthdates, email addresses, associated account IDs, and membership tiers with corresponding benefits.

3. **transactions**: Records customer transactions, detailing account IDs, transaction counts, date ranges, and individual transaction information.

**Relationships between the collections:**

- **customers → accounts**: Each customer is linked to one or more accounts through the `account_id` field, which serves as a foreign key reference to the `account_id` in the `accounts` collection. Each customer may have one or more accounts.
- **accounts → transactions**: Transactions are linked to accounts via `account_id`. Each transaction belongs to a specific account.
- **customers → transactions (indirect)**: Customers and transactions are connected through `account_id` present in both `accounts` and `transactions`. This relationship allows access to customer transactions by first finding their accounts.

Based on the user's query, identify which collections are necessary to construct the appropriate MongoDB query. Return the list of required collection names in JSON format.

Input: {user_question}

**Examples with Explanations:**

- **User Query:** "Retrieve all transactions for customer John Doe."
  - **Explanation:** To retrieve all transactions for John Doe, you first need to identify the customer using the `customers` collection, find their associated accounts from the `accounts` collection, and then retrieve transactions from the `transactions` collection linked to those accounts.
  - **Response:** `["customers", "accounts", "transactions"]`

- **User Query:** "List all products associated with account ID 12345."
  - **Explanation:** This query involves only the `accounts` collection since it contains details about products associated with specific accounts.
  - **Response:** `["accounts"]`

- **User Query:** "Find customers with a credit limit over $10,000."
  - **Explanation:** To find customers with a credit limit over $10,000, you need data from both the `accounts` and `customers` collections because credit limits are stored in `accounts` and are linked to customers.
  - **Response:** `["accounts", "customers"]`

- **User Query:** "Show all transactions between January and March 2023."
  - **Explanation:** This query focuses on retrieving transactions based on a date range, which only involves the `transactions` collection.
  - **Response:** `["transactions"]`

- **User Query:** "Get the email addresses of customers who purchased 'InvestmentStock'."
  - **Explanation:** You need to find customers associated with accounts that purchased 'InvestmentStock' (from the `accounts` collection) and then retrieve their email addresses from the `customers` collection.
  - **Response:** `["accounts", "customers"]`

- **User Query:** "Identify accounts with transactions exceeding $5,000."
  - **Explanation:** This query requires finding transactions over $5,000 from the `transactions` collection and identifying the associated accounts from the `accounts` collection.
  - **Response:** `["transactions", "accounts"]`

- **User Query:** "List all customers residing in Houston, Texas."
  - **Explanation:** This query focuses solely on customer data such as addresses, so only the `customers` collection is needed.
  - **Response:** `["customers"]`

- **User Query:** "Find accounts linked to customers born before 1990."
  - **Explanation:** You need to first filter customers born before 1990 from the `customers` collection and then find their associated accounts from the `accounts` collection.
  - **Response:** `["customers", "accounts"]`

- **User Query:** "Retrieve transactions for accounts with a 'Gold' membership tier."
  - **Explanation:** To retrieve transactions for 'Gold' tier accounts, you need to first find accounts with this tier from the `accounts` collection and then get transactions associated with these accounts from the `transactions` collection.
  - **Response:** `["accounts", "transactions"]`

- **User Query:** "Show all customers who have made more than 50 transactions."
  - **Explanation:** First, find accounts with more than 50 transactions from the `transactions` collection and then identify the associated customers from the `customers` collection using their linked accounts.
  - **Response:** `["transactions", "accounts", "customers"]`

Please provide the list/array of required collection names in JSON format based on the user's query. Do not include any additional information or explanations in the response.
"""


accounts_schema = """ 
The `accounts` collection stores details related to individual customer accounts, with each document containing fields described as follows:
- `_id` (ObjectId): A unique identifier for each account document.
- `account_id` (Integer): The unique ID associated with the customer account.
- `limit` (Integer): The account limit, specifying the maximum allowed credit or balance for the account.
- `products` (Array of Strings): A list of financial products or services associated with the account.

Example Document in the **accounts** collection:
{
  "_id": ObjectId("5ca4bbc7a2dd94ee5816238c"),
  "account_id": 371138,
  "limit": 9000,
  "products": [
    "Derivatives",
    "InvestmentStock"
  ]
}
"""

customers_schema = """
You have a `customers` collection schema with the following structure:
- `_id` (ObjectId): A unique identifier for each customer.
- `username` (String): Represents the customer's username.
- `name` (Object): Contains the customer's full name.
- `address` (String): Stores the customer's address.
- `birthdate` (Date): The birthdate of the customer.
- `email` (String): The email address of the customer.
- `tier_and_details` (Object): Contains detailed membership tiers for customers, with each tier represented as a nested object structure. The structure includes the following attributes:
    - `tier` (String): The name of the membership tier (e.g., "Platinum", "Gold", "Bronze").
    - `benefits` (Array of Strings): A list of benefits associated with the specific tier.
    - `active` (Boolean): Indicates whether the tier is active (true/false).
    - `id` (String): A unique identifier for the tier object.
- `accounts` (Array of Integers): Stores `account_id` values linked to this customer.

Example Document is the **customers** collection:
{
  "_id": {
    "$oid": "5ca4bbcea2dd94ee58162a69"
  },
  "username": "valenciajennifer",
  "name": "Lindsay Cowan",
  "address": "Unit 1047 Box 4089\nDPO AA 57348",
  "birthdate": {
    "$date": "1994-02-19T23:46:27.000Z"
  },
  "email": "cooperalexis@hotmail.com",
  "accounts": [
    116508
  ],
  "tier_and_details": {
    "c06d340a4bad42c59e3b6665571d2907": {
      "tier": "Platinum",
      "benefits": [
        "dedicated account representative"
      ],
      "active": true,
      "id": "c06d340a4bad42c59e3b6665571d2907"
    },
    "5d6a79083c26402bbef823a55d2f4208": {
      "tier": "Bronze",
      "benefits": [
        "car rental insurance",
        "concierge services"
      ],
      "active": true,
      "id": "5d6a79083c26402bbef823a55d2f4208"
    },
    "b754ec2d455143bcb0f0d7bd46de6e06": {
      "tier": "Gold",
      "benefits": [
        "airline lounge access"
      ],
      "active": true,
      "id": "b754ec2d455143bcb0f0d7bd46de6e06"
    }
  }
}
"""

transactions_schema = """
The `transactions` collection stores detailed information about individual transactions, with each document containing fields described as follows:
- `_id` (ObjectId): A unique identifier for each transaction document.
- `account_id` (Integer): The unique account ID associated with the customer.
- `transaction_count` (Integer): The total number of transactions recorded for the account.
- `bucket_start_date` (Date): Represents the start date of a defined bucket period for transactions.
- `bucket_end_date` (Date): Represents the end date of the defined bucket period for transactions.
- `transactions` (Array of Objects): An array containing details of each transaction within the bucket. Each transaction object includes:
  - `date` (Date): The date on which the transaction occurred.
  - `amount` (Integer): The number of units involved in the transaction.
  - `transaction_code` (String): Specifies the type of transaction, such as "buy" or "sell".
  - `symbol` (String): The stock or asset symbol involved in the transaction.
  - `price` (String): The price per unit for the transaction, represented as a string to accommodate high precision.
  - `total` (String): The total value of the transaction, represented as a string to maintain precision for large values.

Example Document in the **transactions** collection:
{
  "_id": ObjectId("5ca4bbc1a2dd94ee58161cb1"),
  "account_id": 443178,
  "transaction_count": 66,
  "bucket_start_date": "1970-01-01T00:00:00Z",
  "bucket_end_date": "2017-01-03T00:00:00Z",
  "transactions": [
    {
      "date": "2003-09-09T00:00:00Z",
      "amount": 7514,
      "transaction_code": "buy",
      "symbol": "adbe",
      "price": "19.1072802650074180519368383102118968963623046875",
      "total": "143572.1039112657392422534031"
    },
    {
      "date": "2016-06-14T00:00:00Z",
      "amount": 9240,
      "transaction_code": "buy",
      "symbol": "team",
      "price": "24.1525632387771480580340721644461154937744140625",
      "total": "223169.6843263008480562348268"
    },
    ...
  ]
}
"""

sales_schema = """
The `sales` collection stores information about individual sales transactions, with each document containing the following fields:

### Fields Description
- `_id` (ObjectId): A unique identifier for the sale document.
- `saleDate` (Date): The date and time of the sale.
- `items` (Array of Objects): A list of items purchased in the sale. Each item object contains:
  - `name` (String): The name of the item.
  - `tags` (Array of Strings): Tags describing the item's category or use (e.g., "office", "school").
  - `price` (Decimal): The price of one/single item (in USD $).
  - `quantity` (Integer): The quantity of the item purchased.
- `storeLocation` (String): The location of the store where the sale occurred (e.g., "Denver").
- `customer` (Object): Information about the customer who made the purchase. The `customer` object includes:
  - `gender` (String): The gender of the customer (e.g., "M", "F").
  - `age` (Integer): The age of the customer.
  - `email` (String): The email address of the customer.
  - `satisfaction` (Integer): A satisfaction rating provided by the customer, ranging from 1 (low) to 5 (high).
- `couponUsed` (Boolean): Indicates whether a coupon was used during the purchase (true/false).
- `purchaseMethod` (String): The method used to complete the purchase (e.g., "Online", "In store", "Phone").

"""

sale_example_query1 = "Retrieve Sales Made in Denver"

sale_example_query_output1 = """
[
    {
        "$match": {
            "storeLocation": "Denver"
        }
    },
    {
        "$project": {
            "_id": 0,
            "saleDate": 1,
            "storeLocation": 1,
            "customer.email": 1
        }
    }
]
"""

sale_example_query2 = "Retrieve the Sale Date, Customer Email, and Total Quantity of Items for Online Purchases"

sale_example_query_output2 = """
[
    {
        "$match": {
            "purchaseMethod": "Online"
        }
    },
    {
        "$addFields": {
            "totalQuantity": {
                "$sum": {
                    "$map": {
                        "input": "$items",
                        "as": "item",
                        "in": "$$item.quantity"
                    }
                }
            }
        }
    },
    {
        "$project": {
            "_id": 0,
            "saleDate": 1,
            "customer.email": 1,
            "totalQuantity": 1
        }
    }
]
"""

sale_query_examples = {'sale_example_query1': sale_example_query1, 'sale_example_output1': sale_example_query_output1, 'sale_example_query2': sale_example_query2, 'sale_example_output2': sale_example_query_output2}

sales_mongodb_prompt = """You are a very intelligent AI assistant who is expert in identifying relevant questions
       from user and converting into nosql mongodb aggregation pipeline query.
       Please use the below schema to write the mongodb queries, don't use any other queries.
    Schema:
       The mentioned mongodb collection talks about various sales related data records including detailed transaction data, including items purchased, customer information, store location, and purchase details.
       The schema for this document represents the structure of the data, describing various properties 
    Here is a breakdown of its schema with descriptions for each field:
    {collection_schema}
    Here are some examples:
        Input1: {sale_example_query1}
        Output1: {sale_example_output1}

        Input2: {sale_example_query2}
        Output2: {sale_example_output2}

    Input: {user_question}
    Today's date is {present_date}
    Important Note:
    1. All dates must be in ISODate bson type and don't use '$date' in queries.
    2. You have to just return the query as to use in aggregation pipeline nothing else. Don't return any other thing.
    3. Always exclude or project the redundant fields in the query.
    4. Handle the empty results, arrays and null values properly so that pipeline query doesn't fail.
    5. Double check the syntax and structure of the query before submitting.
    6. You should handle the boolean values in Python format (Turn true into True and false into False) for the pipeline query.
    """


all_schemas = {'accounts': accounts_schema, 'customers': customers_schema, 'transactions': transactions_schema}

def get_fetch_sales_prompt():
    query_with_prompt_template = PromptTemplate(
        template=sales_mongodb_prompt,
        input_variables=["user_question"]
    ).partial(present_date=datetime.now())

    return query_with_prompt_template

def get_fetch_collections_prompt():
    query_with_prompt_template = PromptTemplate(
        template=fetch_collections_prompt,
        input_variables=["user_question", "sale_example_query1", "sale_example_output1", "sale_example_query2", "sale_example_output2"]
    )

    return query_with_prompt_template


def get_sample_analytics_mongodb_prompt():
    query_with_prompt_template = PromptTemplate(
        template=sample_analytics_mongodb_prompt,
        input_variables=["user_question", "example_query1", "example_query_output1", "example_query2", "example_query_output2", "example_query3", "example_query_output3", "example_query4", "example_query_output4", "collection_schemas"]
    ).partial(present_date=datetime.now())
    return query_with_prompt_template

def get_inspection_prompt(inspection_tools):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                    You are a helpful assistant that quickly evaluates user input and selects appropriate tools to generate a response efficiently. Format the output in CommonMark Markdown, using:
                    - Headers: Use ## for titles and section headers.
                    - Text: Organize into paragraphs, bullet points, tables, and bold text as needed.
                    - Media: Embed images, links, or URLs as appropriate for clarity.
                    - etc.
                    Ensure a concise, accurate response.
                    Note: If you get empty results from a tool, just say "No results found with the given input."
                    The current date is {present_date}.
                """,
            ),
            MessagesPlaceholder(variable_name="message_history_with_input"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(present_date=datetime.now())
    return prompt
