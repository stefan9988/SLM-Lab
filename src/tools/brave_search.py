from config import settings
from langchain_community.tools import BraveSearch

brave_search_tool = BraveSearch.from_api_key(api_key=settings.BRAVE_SEARCH_API_KEY, search_kwargs={"count": 3})