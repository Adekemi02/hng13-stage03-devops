#!/usr/bin/env python3
import os
import re
import time
import requests
from collections import deque
from datetime import datetime, timedelta

# Configuration from environment variables
LOG_FILE = os.environ.get('LOG_FILE', '/var/log/nginx/access.log')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.environ.get('ERROR_RATE_THRESHOLD', 2.0)) / 100
WINDOW_SIZE = int(os.environ.get('WINDOW_SIZE', 5))
ALERT_COOLDOWN_SEC = int(os.environ.get('ALERT_COOLDOWN_SEC', 10))
# MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'false').lower() == 'true'

# State tracking
last_seen_pool = None
last_failover_alert = None
last_error_rate_alert = None
request_window = deque(maxlen=WINDOW_SIZE)
error_window = deque(maxlen=WINDOW_SIZE)

# Regex pattern to parse log lines
log_pattern = re.compile(
    r'pool=(?P<pool>[\w-]+)\s+'
    r'release=(?P<release>[^\s]+)\s+'
    r'upstream_status=(?P<upstream_status>[\d,\s-]+)\s+'
    r'upstream=(?P<upstream>[^\s]+)\s+'
    r'request_time=(?P<request_time>[\d.]+)\s+'
    r'upstream_response_time=(?P<upstream_response_time>[\d.,\s-]+)'
)

# Print the regex pattern to verify it's loaded correctly
print(f"LOG WATCHER: Using regex pattern: {log_pattern.pattern}")

def send_slack_alert(message):
    """Send an alert to Slack via webhook"""
    if not SLACK_WEBHOOK_URL:
        print("Slack webhook URL not configured, skipping alert")
        return
    
    payload = {
        "text": message,
        "username": "Blue-Green Monitor",
        "icon_emoji": ":warning:"
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"Alert sent to Slack: {message}")
    except Exception as e:
        print(f"Failed to send alert to Slack: {e}")

def check_failover(pool):
    """Check if a failover occurred and send alert if needed"""
    global last_seen_pool, last_failover_alert
    
    # We only care about failovers between actual pools, not "-"
    if pool == '-':
        return

    if last_seen_pool and last_seen_pool != pool:
        now = datetime.now()
        
        if last_failover_alert and (now - last_failover_alert) < timedelta(seconds=ALERT_COOLDOWN_SEC):
            print(f"Failover alert in cooldown period, skipping")
            return
        
        message = f"🚨 FAILOVER DETECTED: From: {last_seen_pool.upper()} To: {pool.upper()} Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        send_slack_alert(message)
        last_failover_alert = now
    
    if pool != '-':
        last_seen_pool = pool

def check_error_rate():
    """Check if error rate exceeds threshold and send alert if needed"""
    global last_error_rate_alert
    
    if len(request_window) < WINDOW_SIZE:
        return  # Not enough data yet
    
    error_count = sum(error_window)
    error_rate = error_count / len(request_window)
    
    if error_rate > ERROR_RATE_THRESHOLD:
        now = datetime.now()
        
        if last_error_rate_alert and (now - last_error_rate_alert) < timedelta(seconds=ALERT_COOLDOWN_SEC):
            print(f"Error rate alert in cooldown period, skipping")
            return
        
        message = f"🚨 HIGH ERROR RATE: {error_rate:.2%} ({error_count}/{len(request_window)} requests) Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        send_slack_alert(message)
        last_error_rate_alert = now

def process_log_line(line):
    """Process a single log line"""
    print(f"RAW LOG LINE: {line.strip()}")
    
    match = log_pattern.search(line)
    if not match:
        print("LOG LINE DID NOT MATCH REGEX!")
        return
    
    data = match.groupdict()
    pool = data.get('pool')
    # Handle cases where upstream_status might be '-'
    upstream_status_str = data.get('upstream_status', '0')
    # Split on commas, strip spaces, and convert to integers
    status_codes = [
        int(s.strip()) for s in upstream_status_str.split(',') if s.strip().isdigit()
    ]

    # If *any* of the upstreams failed (>=500), mark it as an error
    is_error = any(code >= 500 for code in status_codes)

    # Debug print
    print(f"PARSED STATUS CODES: {status_codes} -> ERROR={is_error}")

    # Update sliding windows
    request_window.append(1)
    error_window.append(1 if is_error else 0)

    
    # Check for failover
    check_failover(pool)
    
    # Check error rate
    check_error_rate()

def tail_log_file():
    """Tail the log file and process new lines, waiting for it to exist."""
    print(f"Starting log watcher for {LOG_FILE}")
    print(f"Error rate threshold: {ERROR_RATE_THRESHOLD:.2%}")
    print(f"Window size: {WINDOW_SIZE} requests")
    print(f"Alert cooldown: {ALERT_COOLDOWN_SEC} seconds")
    # print(f"Maintenance mode: {MAINTENANCE_MODE}")
    
    print(f"Waiting for log file at '{LOG_FILE}' to become available...")
    
    while True:
        try:
            with open(LOG_FILE, 'r') as f:
                print(f"Log file found. Starting to tail '{LOG_FILE}'")
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    # if MAINTENANCE_MODE:
                    #     continue
                    
                    process_log_line(line)
        
        except FileNotFoundError:
            print(f"Log file not found. Retrying in 5 seconds...")
            time.sleep(5)
        
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Retrying in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    try:
        tail_log_file()
    except KeyboardInterrupt:
        print("Log watcher stopped by user.")
    except Exception as e:
        print(f"Fatal error in log watcher: {e}")