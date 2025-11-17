"""
Parser for extracting structured output from Devin messages.

Since Devin's structured_output field is unreliable, we extract the same
information from the messages where Devin consistently provides it in JSON format.
"""

import json
import re
from typing import Optional, Dict, Any, List


def extract_json_from_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from a message, looking for markdown code blocks.
    
    Args:
        message: The message text to parse
        
    Returns:
        Parsed JSON dict if found, None otherwise
    """
    # Look for JSON in markdown code blocks: ```json ... ```
    json_pattern = r'```json\s*\n(.*?)\n```'
    matches = re.findall(json_pattern, message, re.DOTALL)
    
    if matches:
        # Try to parse the JSON from the code block
        try:
            return json.loads(matches[-1])  # Use the last match
        except json.JSONDecodeError:
            pass
    
    # Fallback: look for raw JSON objects
    json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_obj_pattern, message, re.DOTALL)
    
    for match in reversed(matches):  # Try from last to first
        try:
            data = json.loads(match)
            # Verify it looks like our structured output
            if isinstance(data, dict) and any(key in data for key in ['summary', 'plan', 'confidence']):
                return data
        except json.JSONDecodeError:
            continue
    
    return None


def parse_scoping_from_messages(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Parse scoping output from Devin messages.
    
    Args:
        messages: List of message objects from Devin session
        
    Returns:
        Parsed scoping data if found, None otherwise
    """
    # Get Devin's messages (not user messages)
    devin_messages = [m for m in messages if m.get('type') == 'devin_message']
    
    # Check messages from most recent to oldest
    for message in reversed(devin_messages):
        message_text = message.get('message', '')
        
        # Try to extract JSON
        structured_data = extract_json_from_message(message_text)
        if structured_data:
            # Validate it has the expected scoping fields
            if 'summary' in structured_data or 'plan' in structured_data:
                return structured_data
    
    return None


def parse_execution_from_messages(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Parse execution output from Devin messages.
    
    Args:
        messages: List of message objects from Devin session
        
    Returns:
        Parsed execution data if found, None otherwise
    """
    # Get Devin's messages
    devin_messages = [m for m in messages if m.get('type') == 'devin_message']
    
    # Check messages from most recent to oldest
    for message in reversed(devin_messages):
        message_text = message.get('message', '')
        
        # Try to extract JSON
        structured_data = extract_json_from_message(message_text)
        if structured_data:
            # Validate it has the expected execution fields
            if 'status' in structured_data or 'branch' in structured_data:
                return structured_data
    
    return None


def extract_text_summary(messages: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract a text summary from the last Devin message.
    
    Useful when no JSON is found but we want to show something to the user.
    
    Args:
        messages: List of message objects from Devin session
        
    Returns:
        Summary text if found, None otherwise
    """
    devin_messages = [m for m in messages if m.get('type') == 'devin_message']
    
    if devin_messages:
        # Return the last Devin message
        last_message = devin_messages[-1].get('message', '')
        # Remove JSON code blocks for cleaner display
        cleaned = re.sub(r'```json.*?```', '', last_message, flags=re.DOTALL)
        return cleaned.strip()
    
    return None

