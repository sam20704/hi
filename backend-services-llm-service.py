from openai import AzureOpenAI
from app.core.config import settings


class LLMService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )

    async def nl_to_sql(self, question: str) -> str:
        """
        Convert natural language question to SQL
        """
        system_prompt = """
You are an expert SAP database assistant.
Generate ONLY a single SQLite SELECT query.
Rules:
- Use only SELECT
- No INSERT, UPDATE, DELETE
- No semicolons
- Use existing table names only
Tables:
customers(customer_id, customer_name, country, city, credit_limit, customer_group)
sales_orders(order_id, customer_id, order_date, total_amount, currency, status, sales_org)
sales_order_items(order_id, item_number, material_id, quantity, unit_price, net_value, delivery_date)
materials(material_id, material_name, material_type, base_unit, material_group, created_date)
inventory(material_id, plant, storage_location, quantity, unit, last_updated)
purchase_orders(po_number, vendor_id, po_date, total_amount, currency, status)
"""

        response = self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=200,
        )

        sql = response.choices[0].message.content.strip()
        return sql

    async def summarize_results(self, question: str, columns: list, rows: list) -> str:
        """
        Summarize SQL results for humans
        """
        preview = rows[:5]

        prompt = f"""
User question:
{question}

Columns:
{columns}

Sample rows:
{preview}

Explain the result in simple business language.
"""

        response = self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )

        return response.choices[0].message.content.strip()
