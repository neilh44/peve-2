import logging
from datetime import datetime, timedelta
from google_calendar_manager import GoogleCalendarScheduler

logger = logging.getLogger(__name__)

class AppointmentManager:
    def __init__(self, client_secret_path):
        self.calendar_scheduler = GoogleCalendarScheduler(client_secret_path)

    async def reschedule_appointment(self, current_appointment, new_date_time):
        try:
            logger.info(f"Attempting to reschedule appointment: {current_appointment} to {new_date_time}")
            start_time, end_time = self.parse_datetime(new_date_time)
            if not start_time or not end_time:
                return "Invalid date or time provided for rescheduling."

            event_result = await self.calendar_scheduler.reschedule_event(current_appointment, start_time, end_time)
            logger.info(f"Rescheduled event result: {event_result}")
            return f"Your appointment has been successfully rescheduled to {datetime.fromisoformat(start_time).strftime('%A, %B %d, %Y at %I:%M %p')}."
        except Exception as e:
            logger.error(f"Failed to reschedule appointment: {e}")
            return "Sorry, there was an issue rescheduling your appointment. Please try again later."

    async def cancel_appointment(self, appointment_to_cancel):
        try:
            logger.info(f"Attempting to cancel appointment: {appointment_to_cancel}")
            await self.calendar_scheduler.cancel_event(appointment_to_cancel)
            return "Your appointment has been successfully canceled."
        except Exception as e:
            logger.error(f"Failed to cancel appointment: {e}")
            return "Sorry, there was an issue canceling your appointment. Please try again later."

    def parse_datetime(self, datetime_str):
        import re

        date = None
        time = None

        # Regular expressions for date and time
        date_pattern = re.compile(r'\b(\d{1,2}[a-z]{2}\s\w+|\w+\s\d{1,2}(?:,\s\d{4})?)\b')
        time_pattern = re.compile(r'\b(\d{1,2}:\d{2}\s*[APM]{2})\b')

        date_match = date_pattern.search(datetime_str)
        time_match = time_pattern.search(datetime_str)

        if date_match:
            date = date_match.group(0)
        if time_match:
            time = time_match.group(0)

        if date and time:
            date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date)
            datetime_str = f"{date} {time}"

            formats = [
                "%d %B %Y %I:%M %p",
                "%B %d, %Y %I:%M %p",
                "%B %d %I:%M %p",
                "%d %B %I:%M %p"
            ]

            for fmt in formats:
                try:
                    start_time = datetime.strptime(datetime_str, fmt)
                    end_time = start_time + timedelta(hours=1)
                    return start_time.isoformat(), end_time.isoformat()
                except ValueError:
                    continue
        logger.warning(f"Failed to parse datetime from string: {datetime_str}")
        return None, None
