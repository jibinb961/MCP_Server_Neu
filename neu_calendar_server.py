from mcp.server.fastmcp import FastMCP
import os
import json
import datetime
import httpx
from icalendar import Calendar
from typing import List, Dict, Any, Optional, Union
import textwrap
import sys
import re

# Create an MCP server
mcp = FastMCP("NEU Calendar Service")

# URL for the Northeastern University calendar ICS file
CALENDAR_URL = "https://calendar.northeastern.edu/search/events.ics"

# Cache for the calendar data to avoid fetching it too often
calendar_cache = {
    "last_fetch": None,
    "data": None,
    "cache_duration": datetime.timedelta(hours=1)  # Cache for 1 hour
}

async def fetch_calendar_data():
    """
    Fetch the calendar data from the Northeastern University calendar.
    Uses caching to avoid fetching the data too often.
    """
    now = datetime.datetime.now()
    
    # Check if we need to refresh the cache
    if (calendar_cache["last_fetch"] is None or 
        calendar_cache["data"] is None or 
        now - calendar_cache["last_fetch"] > calendar_cache["cache_duration"]):
        
        try:
            print(f"Fetching calendar data from {CALENDAR_URL}", file=sys.stderr)
            async with httpx.AsyncClient() as client:
                response = await client.get(CALENDAR_URL)
                response.raise_for_status()
                
                # Parse the ICS data
                cal = Calendar.from_ical(response.text)
                
                # Update the cache
                calendar_cache["last_fetch"] = now
                calendar_cache["data"] = cal
                
                return cal
        except Exception as e:
            print(f"Error fetching calendar data: {str(e)}", file=sys.stderr)
            if calendar_cache["data"] is not None:
                # Return cached data if available, even if it's stale
                print("Using stale cached data", file=sys.stderr)
                return calendar_cache["data"]
            raise Exception(f"Failed to fetch calendar data: {str(e)}")
    
    return calendar_cache["data"]

def extract_event_details(component):
    """
    Extract details from an iCalendar event component.
    """
    try:
        event_summary = str(component.get("SUMMARY", ""))
        
        # Handle start date/time with better error handling
        try:
            event_start = component.get("DTSTART")
            if event_start:
                event_start = event_start.dt
                # Convert to date if it's a datetime
                if isinstance(event_start, datetime.datetime):
                    event_start_date = event_start.date()
                    event_start_time = event_start.strftime("%H:%M")
                else:
                    event_start_date = event_start
                    event_start_time = None
            else:
                event_start_date = None
                event_start_time = None
        except Exception as e:
            print(f"Error parsing start date for event '{event_summary}': {str(e)}", file=sys.stderr)
            event_start_date = None
            event_start_time = None
        
        # Handle end date/time with better error handling
        try:
            event_end = component.get("DTEND")
            if event_end:
                event_end = event_end.dt
                # Convert to date if it's a datetime
                if isinstance(event_end, datetime.datetime):
                    event_end_date = event_end.date()
                    event_end_time = event_end.strftime("%H:%M")
                else:
                    event_end_date = event_end
                    event_end_time = None
            else:
                event_end_date = None
                event_end_time = None
        except Exception as e:
            print(f"Error parsing end date for event '{event_summary}': {str(e)}", file=sys.stderr)
            event_end_date = None
            event_end_time = None
        
        # Extract other details with robust error handling
        try:
            event_location = str(component.get("LOCATION", ""))
        except Exception:
            event_location = ""
            
        try:
            event_description = str(component.get("DESCRIPTION", ""))
        except Exception:
            event_description = ""
            
        try:
            event_url = str(component.get("URL", ""))
        except Exception:
            event_url = ""
        
        # Fix geo location handling with multiple formats
        geo_data = None
        try:
            geo = component.get("GEO")
            if geo:
                # For vGeo objects, try to use the latitude and longitude attributes
                if hasattr(geo, 'latitude') and hasattr(geo, 'longitude'):
                    geo_data = {"latitude": float(geo.latitude), "longitude": float(geo.longitude)}
                # For tuple-like objects, try to unpack
                elif hasattr(geo, '__iter__') and len(geo) >= 2:
                    latitude, longitude = geo[0], geo[1]
                    geo_data = {"latitude": float(latitude), "longitude": float(longitude)}
                # For string representations with semicolons
                elif isinstance(geo, str) and ';' in geo:
                    parts = geo.split(';')
                    if len(parts) >= 2:
                        geo_data = {"latitude": float(parts[0]), "longitude": float(parts[1])}
                # For other string representations, try to extract numbers
                elif isinstance(geo, str):
                    numbers = re.findall(r'[-+]?\d*\.\d+|\d+', geo)
                    if len(numbers) >= 2:
                        geo_data = {"latitude": float(numbers[0]), "longitude": float(numbers[1])}
        except Exception as e:
            print(f"Error parsing geo data for event '{event_summary}': {str(e)}", file=sys.stderr)
            geo_data = None
        
        # Extract categories with better handling of various formats
        categories = []
        try:
            raw_categories = component.get("CATEGORIES")
            if raw_categories:
                # Handle different formats of categories
                if isinstance(raw_categories, list):
                    # Some ICS files store categories as list
                    for cat_item in raw_categories:
                        if isinstance(cat_item, str):
                            categories.extend([c.strip() for c in cat_item.split(',') if c.strip()])
                        elif hasattr(cat_item, 'cats'): 
                            # Some icalendar implementations use a custom object
                            categories.extend([c.strip() for c in cat_item.cats if c.strip()])
                # Try to decode if it's in binary format
                elif isinstance(raw_categories, bytes):
                    try:
                        decoded = raw_categories.decode("utf-8")
                        categories = [cat.strip() for cat in decoded.split(",") if cat.strip()]
                    except:
                        categories = [cat.strip() for cat in str(raw_categories).split(",") if cat.strip()]
                # Handle string formats
                elif isinstance(raw_categories, str):
                    categories = [cat.strip() for cat in raw_categories.split(",") if cat.strip()]
                # Other object with direct attribute access
                elif hasattr(raw_categories, 'cats'):
                    categories = [cat.strip() for cat in raw_categories.cats if cat.strip()]
        except Exception as e:
            print(f"Error parsing categories for event '{event_summary}': {str(e)}", file=sys.stderr)
            categories = []
        
        # Create the event details dictionary
        event_details = {
            "summary": event_summary,
            "start_date": event_start_date.strftime("%Y-%m-%d") if event_start_date else None,
            "start_time": event_start_time,
            "end_date": event_end_date.strftime("%Y-%m-%d") if event_end_date else None,
            "end_time": event_end_time,
            "location": event_location,
            "description": event_description,
            "url": event_url,
            "geo": geo_data,
            "categories": categories
        }
        
        return event_details
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error parsing event: {str(e)}", file=sys.stderr)
        # Return a minimal event with the summary if available
        return {
            "summary": str(component.get("SUMMARY", "Unknown Event")),
            "start_date": None,
            "start_time": None,
            "end_date": None,
            "end_time": None,
            "location": "",
            "description": "",
            "url": "",
            "geo": None,
            "categories": []
        }

async def get_all_events():
    """
    Get all events from the calendar.
    """
    cal = await fetch_calendar_data()
    events = []
    
    for component in cal.walk():
        if component.name == "VEVENT":
            event_details = extract_event_details(component)
            events.append(event_details)
    
    # Sort by start date
    events.sort(key=lambda x: x["start_date"] if x["start_date"] else "9999-12-31")
    
    return events

@mcp.tool()
async def get_today_events() -> str:
    """
    Get all events happening today at Northeastern University.
    
    Returns:
        A formatted string containing details of today's events
    """
    try:
        all_events = await get_all_events()
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        today_events = [
            event for event in all_events 
            if event["start_date"] == today
        ]
        
        if not today_events:
            return "No events scheduled for today."
        
        result = f"Events for today ({today}):\n\n"
        for i, event in enumerate(today_events, 1):
            time_str = f" at {event['start_time']}" if event['start_time'] else ""
            location_str = f"\nLocation: {event['location']}" if event['location'] else ""
            
            result += (
                f"{i}. {event['summary']}{time_str}{location_str}\n"
                f"   URL: {event['url']}\n\n"
            )
        
        return result
    
    except Exception as e:
        return f"Error retrieving today's events: {str(e)}"

@mcp.tool()
async def get_upcoming_events(days: int = 7) -> str:
    """
    Get upcoming events at Northeastern University for the specified number of days.
    
    Args:
        days: Number of days ahead to look for events (default: 7)
    
    Returns:
        A formatted string containing details of upcoming events
    """
    try:
        all_events = await get_all_events()
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=days)
        
        today_str = today.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        upcoming_events = [
            event for event in all_events 
            if event["start_date"] and today_str <= event["start_date"] <= end_date_str
        ]
        
        if not upcoming_events:
            return f"No events scheduled for the next {days} days."
        
        result = f"Upcoming events for the next {days} days:\n\n"
        
        # Group events by date
        events_by_date = {}
        for event in upcoming_events:
            date = event["start_date"]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        # Sort dates and display events
        for date in sorted(events_by_date.keys()):
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            day_name = date_obj.strftime("%A")
            result += f"--- {day_name}, {date} ---\n"
            
            for event in events_by_date[date]:
                time_str = f" at {event['start_time']}" if event['start_time'] else ""
                location_str = f"\n   Location: {event['location']}" if event['location'] else ""
                
                result += (
                    f"* {event['summary']}{time_str}{location_str}\n"
                    f"  URL: {event['url']}\n\n"
                )
        
        return result
    
    except Exception as e:
        return f"Error retrieving upcoming events: {str(e)}"

@mcp.tool()
async def search_events(query: str, days: int = 30) -> str:
    """
    Search for events at Northeastern University that match the given query.
    
    Args:
        query: Search term to look for in event titles and descriptions
        days: Number of days ahead to look for events (default: 30)
    
    Returns:
        A formatted string containing matching events
    """
    try:
        all_events = await get_all_events()
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=days)
        
        today_str = today.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Filter events by date range and query
        query = query.lower()
        matching_events = [
            event for event in all_events 
            if (event["start_date"] and today_str <= event["start_date"] <= end_date_str) and
               (query in event["summary"].lower() or query in event["description"].lower())
        ]
        
        if not matching_events:
            return f"No events matching '{query}' found in the next {days} days."
        
        result = f"Events matching '{query}' in the next {days} days:\n\n"
        
        for i, event in enumerate(matching_events, 1):
            date_str = event["start_date"] if event["start_date"] else "No date"
            time_str = f" at {event['start_time']}" if event['start_time'] else ""
            location_str = f"\nLocation: {event['location']}" if event['location'] else ""
            
            result += (
                f"{i}. {event['summary']} ({date_str}{time_str}){location_str}\n"
                f"   URL: {event['url']}\n\n"
            )
        
        return result
    
    except Exception as e:
        return f"Error searching events: {str(e)}"

@mcp.tool()
async def get_events_by_category(category: str, days: int = 30) -> str:
    """
    Get events at Northeastern University filtered by category.
    
    Args:
        category: Category to filter events by (e.g., "Athletics", "Workshop")
        days: Number of days ahead to look for events (default: 30)
    
    Returns:
        A formatted string containing events in the specified category
    """
    try:
        all_events = await get_all_events()
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=days)
        
        today_str = today.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Filter events by date range and category
        category = category.lower()
        category_events = [
            event for event in all_events 
            if (event["start_date"] and today_str <= event["start_date"] <= end_date_str) and
               any(category in cat.lower() for cat in event["categories"])
        ]
        
        if not category_events:
            return f"No events in category '{category}' found in the next {days} days."
        
        result = f"Events in category '{category}' for the next {days} days:\n\n"
        
        # Group events by date
        events_by_date = {}
        for event in category_events:
            date = event["start_date"]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        # Sort dates and display events
        for date in sorted(events_by_date.keys()):
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            day_name = date_obj.strftime("%A")
            result += f"--- {day_name}, {date} ---\n"
            
            for event in events_by_date[date]:
                time_str = f" at {event['start_time']}" if event['start_time'] else ""
                location_str = f"\n   Location: {event['location']}" if event['location'] else ""
                
                result += (
                    f"* {event['summary']}{time_str}{location_str}\n"
                    f"  URL: {event['url']}\n\n"
                )
        
        return result
    
    except Exception as e:
        return f"Error retrieving events by category: {str(e)}"

@mcp.tool()
async def get_event_details(event_name: str) -> str:
    """
    Get detailed information about a specific event at Northeastern University.
    
    Args:
        event_name: Name or part of the name of the event to find
    
    Returns:
        A formatted string containing detailed information about the event
    """
    try:
        all_events = await get_all_events()
        event_name_lower = event_name.lower()
        
        # Find events that match the name
        matching_events = [
            event for event in all_events 
            if event_name_lower in event["summary"].lower()
        ]
        
        if not matching_events:
            return f"No events found matching '{event_name}'."
        
        # If multiple events match, return information for all of them
        result = f"Details for events matching '{event_name}':\n\n"
        
        for i, event in enumerate(matching_events, 1):
            date_str = event["start_date"] if event["start_date"] else "No date"
            start_time = f" at {event['start_time']}" if event['start_time'] else ""
            end_time = f" to {event['end_time']}" if event['end_time'] else ""
            location = f"Location: {event['location']}\n" if event['location'] else ""
            categories = f"Categories: {', '.join(event['categories'])}\n" if event['categories'] else ""
            geo = f"Coordinates: {event['geo']['latitude']}, {event['geo']['longitude']}\n" if event['geo'] else ""
            
            # Clean up description text
            description = event["description"].replace("\\n", "\n").replace("\\,", ",")
            
            result += (
                f"--- Event {i}: {event['summary']} ---\n"
                f"Date: {date_str}{start_time}{end_time}\n"
                f"{location}"
                f"{categories}"
                f"{geo}"
                f"URL: {event['url']}\n\n"
                f"Description:\n{textwrap.fill(description, width=80)}\n\n"
                f"{'-' * 80}\n\n"
            )
        
        return result
    
    except Exception as e:
        return f"Error retrieving event details: {str(e)}"

@mcp.tool()
async def list_categories() -> str:
    """
    List all available event categories at Northeastern University.
    
    Returns:
        A formatted string containing all available categories
    """
    try:
        all_events = await get_all_events()
        
        # Extract all categories
        all_categories = set()
        for event in all_events:
            for category in event["categories"]:
                if category:  # Ensure non-empty
                    all_categories.add(category)
        
        if not all_categories:
            return "No categories found in the calendar."
        
        # Sort categories alphabetically
        sorted_categories = sorted(all_categories)
        
        result = "Available event categories:\n\n"
        for i, category in enumerate(sorted_categories, 1):
            result += f"{i}. {category}\n"
        
        return result
    
    except Exception as e:
        return f"Error listing categories: {str(e)}"

@mcp.prompt()
async def help():
    """Get help on using the NEU Calendar MCP service"""
    return {
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": "Please explain how to use this Northeastern University Calendar MCP server. What tools are available and how do I use them?"
                }
            }
        ]
    }

@mcp.resource("about://service")
def get_about_service():
    """Provides information about this MCP service"""
    return (
        "# Northeastern University Calendar MCP Service\n\n"
        "This MCP service provides tools to access and search the Northeastern University event calendar. "
        "The service fetches data from the official Northeastern University calendar feed and provides "
        "convenient tools to find and filter events.\n\n"
        "## Available Tools\n\n"
        "- `get_today_events`: Get all events happening today\n"
        "- `get_upcoming_events`: Get events for the next N days\n"
        "- `search_events`: Search for events matching a query\n"
        "- `get_events_by_category`: Get events in a specific category\n"
        "- `get_event_details`: Get detailed information about a specific event\n"
        "- `list_categories`: List all available event categories\n\n"
        "Use the `/help` prompt to get more detailed assistance.\n\n"
        "Data source: https://calendar.northeastern.edu/"
    ), "text/markdown"

if __name__ == "__main__":
    # When running directly, start the server
    mcp.run() 