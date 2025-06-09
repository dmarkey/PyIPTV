#!/usr/bin/env python3
"""
Geolocation Manager for PyIPTV

This module provides geolocation-based automatic subtitle track selection.
It detects the user's location and automatically selects appropriate subtitle
languages based on country-specific preferences.
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtCore import QUrl


class GeolocationResult:
    """Result of geolocation detection."""
    
    def __init__(self, country_code: str = "", country_name: str = "", 
                 city: str = "", region: str = "", timezone: str = "",
                 latitude: float = 0.0, longitude: float = 0.0):
        self.country_code = country_code.upper()
        self.country_name = country_name
        self.city = city
        self.region = region
        self.timezone = timezone
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = time.time()
        self.is_valid = bool(country_code)


class CountryLanguageMapper:
    """Maps countries to their preferred subtitle languages."""
    
    # Country code to preferred languages mapping
    COUNTRY_LANGUAGE_MAP = {
        # Arabic countries
        'DZ': ['ar', 'fr'],  # Algeria - Arabic, French
        'BH': ['ar', 'en'],  # Bahrain - Arabic, English
        'EG': ['ar', 'en'],  # Egypt - Arabic, English
        'IQ': ['ar', 'en'],  # Iraq - Arabic, English
        'JO': ['ar', 'en'],  # Jordan - Arabic, English
        'KW': ['ar', 'en'],  # Kuwait - Arabic, English
        'LB': ['ar', 'fr', 'en'],  # Lebanon - Arabic, French, English
        'LY': ['ar', 'en'],  # Libya - Arabic, English
        'MA': ['ar', 'fr'],  # Morocco - Arabic, French
        'OM': ['ar', 'en'],  # Oman - Arabic, English
        'PS': ['ar', 'en'],  # Palestine - Arabic, English
        'QA': ['ar', 'en'],  # Qatar - Arabic, English
        'SA': ['ar', 'en'],  # Saudi Arabia - Arabic, English
        'SD': ['ar', 'en'],  # Sudan - Arabic, English
        'SY': ['ar', 'en'],  # Syria - Arabic, English
        'TN': ['ar', 'fr'],  # Tunisia - Arabic, French
        'AE': ['ar', 'en'],  # UAE - Arabic, English
        'YE': ['ar', 'en'],  # Yemen - Arabic, English
        
        # European countries
        'FR': ['fr', 'en'],  # France - French, English
        'DE': ['de', 'en'],  # Germany - German, English
        'ES': ['es', 'en'],  # Spain - Spanish, English
        'IT': ['it', 'en'],  # Italy - Italian, English
        'PT': ['pt', 'en'],  # Portugal - Portuguese, English
        'NL': ['nl', 'en'],  # Netherlands - Dutch, English
        'BE': ['nl', 'fr', 'en'],  # Belgium - Dutch, French, English
        'CH': ['de', 'fr', 'it', 'en'],  # Switzerland - German, French, Italian, English
        'AT': ['de', 'en'],  # Austria - German, English
        'PL': ['pl', 'en'],  # Poland - Polish, English
        'CZ': ['cs', 'en'],  # Czech Republic - Czech, English
        'SK': ['sk', 'en'],  # Slovakia - Slovak, English
        'HU': ['hu', 'en'],  # Hungary - Hungarian, English
        'RO': ['ro', 'en'],  # Romania - Romanian, English
        'BG': ['bg', 'en'],  # Bulgaria - Bulgarian, English
        'HR': ['hr', 'en'],  # Croatia - Croatian, English
        'SI': ['sl', 'en'],  # Slovenia - Slovenian, English
        'RS': ['sr', 'en'],  # Serbia - Serbian, English
        'BA': ['bs', 'hr', 'sr', 'en'],  # Bosnia - Bosnian, Croatian, Serbian, English
        'MK': ['mk', 'en'],  # North Macedonia - Macedonian, English
        'AL': ['sq', 'en'],  # Albania - Albanian, English
        'GR': ['el', 'en'],  # Greece - Greek, English
        'TR': ['tr', 'en'],  # Turkey - Turkish, English
        'RU': ['ru', 'en'],  # Russia - Russian, English
        'UA': ['uk', 'ru', 'en'],  # Ukraine - Ukrainian, Russian, English
        'BY': ['be', 'ru', 'en'],  # Belarus - Belarusian, Russian, English
        'LT': ['lt', 'en'],  # Lithuania - Lithuanian, English
        'LV': ['lv', 'en'],  # Latvia - Latvian, English
        'EE': ['et', 'en'],  # Estonia - Estonian, English
        'FI': ['fi', 'sv', 'en'],  # Finland - Finnish, Swedish, English
        'SE': ['sv', 'en'],  # Sweden - Swedish, English
        'NO': ['no', 'en'],  # Norway - Norwegian, English
        'DK': ['da', 'en'],  # Denmark - Danish, English
        'IS': ['is', 'en'],  # Iceland - Icelandic, English
        
        # Asian countries
        'CN': ['zh', 'en'],  # China - Chinese, English
        'JP': ['ja', 'en'],  # Japan - Japanese, English
        'KR': ['ko', 'en'],  # South Korea - Korean, English
        'IN': ['hi', 'en'],  # India - Hindi, English
        'TH': ['th', 'en'],  # Thailand - Thai, English
        'VN': ['vi', 'en'],  # Vietnam - Vietnamese, English
        'ID': ['id', 'en'],  # Indonesia - Indonesian, English
        'MY': ['ms', 'en'],  # Malaysia - Malay, English
        'SG': ['en', 'zh', 'ms'],  # Singapore - English, Chinese, Malay
        'PH': ['en', 'tl'],  # Philippines - English, Filipino
        'TW': ['zh', 'en'],  # Taiwan - Chinese, English
        'HK': ['zh', 'en'],  # Hong Kong - Chinese, English
        'MO': ['zh', 'pt', 'en'],  # Macau - Chinese, Portuguese, English
        
        # Americas
        'US': ['en', 'es'],  # United States - English, Spanish
        'CA': ['en', 'fr'],  # Canada - English, French
        'MX': ['es', 'en'],  # Mexico - Spanish, English
        'BR': ['pt', 'en'],  # Brazil - Portuguese, English
        'AR': ['es', 'en'],  # Argentina - Spanish, English
        'CL': ['es', 'en'],  # Chile - Spanish, English
        'CO': ['es', 'en'],  # Colombia - Spanish, English
        'PE': ['es', 'en'],  # Peru - Spanish, English
        'VE': ['es', 'en'],  # Venezuela - Spanish, English
        'UY': ['es', 'en'],  # Uruguay - Spanish, English
        'PY': ['es', 'en'],  # Paraguay - Spanish, English
        'BO': ['es', 'en'],  # Bolivia - Spanish, English
        'EC': ['es', 'en'],  # Ecuador - Spanish, English
        
        # Africa
        'ZA': ['en', 'af'],  # South Africa - English, Afrikaans
        'NG': ['en'],  # Nigeria - English
        'KE': ['en', 'sw'],  # Kenya - English, Swahili
        'GH': ['en'],  # Ghana - English
        'ET': ['am', 'en'],  # Ethiopia - Amharic, English
        'TZ': ['sw', 'en'],  # Tanzania - Swahili, English
        'UG': ['en', 'sw'],  # Uganda - English, Swahili
        'RW': ['rw', 'en', 'fr'],  # Rwanda - Kinyarwanda, English, French
        'SN': ['fr', 'wo'],  # Senegal - French, Wolof
        'CI': ['fr'],  # Ivory Coast - French
        'ML': ['fr'],  # Mali - French
        'BF': ['fr'],  # Burkina Faso - French
        'NE': ['fr'],  # Niger - French
        'TD': ['fr', 'ar'],  # Chad - French, Arabic
        'CM': ['fr', 'en'],  # Cameroon - French, English
        'GA': ['fr'],  # Gabon - French
        'CG': ['fr'],  # Republic of Congo - French
        'CD': ['fr'],  # Democratic Republic of Congo - French
        'CF': ['fr'],  # Central African Republic - French
        'AO': ['pt'],  # Angola - Portuguese
        'MZ': ['pt'],  # Mozambique - Portuguese
        'GW': ['pt'],  # Guinea-Bissau - Portuguese
        'CV': ['pt'],  # Cape Verde - Portuguese
        'ST': ['pt'],  # São Tomé and Príncipe - Portuguese
        
        # Oceania
        'AU': ['en'],  # Australia - English
        'NZ': ['en'],  # New Zealand - English
        'FJ': ['en', 'fj'],  # Fiji - English, Fijian
        'PG': ['en'],  # Papua New Guinea - English
        'SB': ['en'],  # Solomon Islands - English
        'VU': ['en', 'fr'],  # Vanuatu - English, French
        'NC': ['fr'],  # New Caledonia - French
        'PF': ['fr'],  # French Polynesia - French
    }
    
    @classmethod
    def get_preferred_languages(cls, country_code: str) -> List[str]:
        """Get preferred subtitle languages for a country."""
        return cls.COUNTRY_LANGUAGE_MAP.get(country_code.upper(), ['en'])
    
    @classmethod
    def get_language_name(cls, language_code: str) -> str:
        """Get human-readable language name from code."""
        language_names = {
            'ar': 'Arabic', 'en': 'English', 'fr': 'French', 'de': 'German',
            'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch',
            'pl': 'Polish', 'cs': 'Czech', 'sk': 'Slovak', 'hu': 'Hungarian',
            'ro': 'Romanian', 'bg': 'Bulgarian', 'hr': 'Croatian', 'sl': 'Slovenian',
            'sr': 'Serbian', 'bs': 'Bosnian', 'mk': 'Macedonian', 'sq': 'Albanian',
            'el': 'Greek', 'tr': 'Turkish', 'ru': 'Russian', 'uk': 'Ukrainian',
            'be': 'Belarusian', 'lt': 'Lithuanian', 'lv': 'Latvian', 'et': 'Estonian',
            'fi': 'Finnish', 'sv': 'Swedish', 'no': 'Norwegian', 'da': 'Danish',
            'is': 'Icelandic', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean',
            'hi': 'Hindi', 'th': 'Thai', 'vi': 'Vietnamese', 'id': 'Indonesian',
            'ms': 'Malay', 'tl': 'Filipino', 'af': 'Afrikaans', 'sw': 'Swahili',
            'am': 'Amharic', 'rw': 'Kinyarwanda', 'wo': 'Wolof', 'fj': 'Fijian'
        }
        return language_names.get(language_code.lower(), language_code.upper())


class GeolocationDetector(QThread):
    """Thread for detecting user's geolocation."""
    
    # Signals
    location_detected = Signal(object)  # GeolocationResult
    detection_failed = Signal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager()
        
    def run(self):
        """Detect user's location using IP geolocation service."""
        try:
            # Use a free IP geolocation service
            url = QUrl("http://ip-api.com/json/")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, 
                            "PyIPTV/1.0 (Geolocation)")
            
            reply = self.network_manager.get(request)
            
            # Wait for response (simplified for thread)
            while not reply.isFinished():
                self.msleep(100)
            
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = reply.readAll().data().decode('utf-8')
                self._parse_geolocation_response(data)
            else:
                self.detection_failed.emit(f"Network error: {reply.errorString()}")
                
        except Exception as e:
            self.detection_failed.emit(str(e))
    
    def _parse_geolocation_response(self, response_data: str):
        """Parse the geolocation API response."""
        try:
            data = json.loads(response_data)
            
            if data.get('status') == 'success':
                result = GeolocationResult(
                    country_code=data.get('countryCode', ''),
                    country_name=data.get('country', ''),
                    city=data.get('city', ''),
                    region=data.get('regionName', ''),
                    timezone=data.get('timezone', ''),
                    latitude=data.get('lat', 0.0),
                    longitude=data.get('lon', 0.0)
                )
                self.location_detected.emit(result)
            else:
                self.detection_failed.emit(f"Geolocation failed: {data.get('message', 'Unknown error')}")
                
        except json.JSONDecodeError as e:
            self.detection_failed.emit(f"Failed to parse geolocation response: {e}")


class GeolocationManager(QObject):
    """Manager for geolocation-based subtitle selection."""
    
    # Signals
    location_updated = Signal(object)  # GeolocationResult
    preferred_languages_changed = Signal(list)  # List of language codes
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.current_location = None
        self.preferred_languages = ['en']  # Default to English
        self.detection_thread = None
        
        # Auto-detection timer (check location periodically)
        self.auto_detection_timer = QTimer()
        self.auto_detection_timer.timeout.connect(self.detect_location)
        
        # Load cached location
        self._load_cached_location()
        
        # Setup auto-detection if enabled
        self._setup_auto_detection()
    
    def _load_cached_location(self):
        """Load previously detected location from settings."""
        cached_data = self.settings_manager.get_setting("cached_geolocation")
        if cached_data:
            try:
                # Check if cache is still valid (24 hours)
                if time.time() - cached_data.get('timestamp', 0) < 24 * 3600:
                    self.current_location = GeolocationResult(
                        country_code=cached_data.get('country_code', ''),
                        country_name=cached_data.get('country_name', ''),
                        city=cached_data.get('city', ''),
                        region=cached_data.get('region', ''),
                        timezone=cached_data.get('timezone', ''),
                        latitude=cached_data.get('latitude', 0.0),
                        longitude=cached_data.get('longitude', 0.0)
                    )
                    self.current_location.timestamp = cached_data.get('timestamp', time.time())
                    self._update_preferred_languages()
            except Exception as e:
                print(f"Error loading cached location: {e}")
    
    def _setup_auto_detection(self):
        """Setup automatic location detection."""
        auto_detect = self.settings_manager.get_setting("geolocation_auto_detect")
        if auto_detect is None:
            auto_detect = True

        if auto_detect:
            # Check location every 24 hours
            interval_hours = self.settings_manager.get_setting("geolocation_check_interval_hours")
            if interval_hours is None:
                interval_hours = 24
            self.auto_detection_timer.start(interval_hours * 60 * 60 * 1000)

            # Detect immediately if no cached location
            if not self.current_location:
                QTimer.singleShot(1000, self.detect_location)  # Delay to let app start
    
    def detect_location(self):
        """Start location detection."""
        if self.detection_thread and self.detection_thread.isRunning():
            return  # Already detecting
        
        self.detection_thread = GeolocationDetector()
        self.detection_thread.location_detected.connect(self._on_location_detected)
        self.detection_thread.detection_failed.connect(self._on_detection_failed)
        self.detection_thread.start()
    
    def _on_location_detected(self, location: GeolocationResult):
        """Handle successful location detection."""
        self.current_location = location
        self._update_preferred_languages()
        self._cache_location()
        self.location_updated.emit(location)
        print(f"Location detected: {location.city}, {location.country_name} ({location.country_code})")
    
    def _on_detection_failed(self, error_message: str):
        """Handle location detection failure."""
        print(f"Geolocation detection failed: {error_message}")
        # Fall back to default languages if no cached location
        if not self.current_location:
            self.preferred_languages = ['en']
            self.preferred_languages_changed.emit(self.preferred_languages)
    
    def _update_preferred_languages(self):
        """Update preferred languages based on current location."""
        if self.current_location and self.current_location.is_valid:
            self.preferred_languages = CountryLanguageMapper.get_preferred_languages(
                self.current_location.country_code
            )
            self.preferred_languages_changed.emit(self.preferred_languages)
    
    def _cache_location(self):
        """Cache the current location in settings."""
        if self.current_location:
            cache_data = {
                'country_code': self.current_location.country_code,
                'country_name': self.current_location.country_name,
                'city': self.current_location.city,
                'region': self.current_location.region,
                'timezone': self.current_location.timezone,
                'latitude': self.current_location.latitude,
                'longitude': self.current_location.longitude,
                'timestamp': self.current_location.timestamp
            }
            self.settings_manager.set_setting("cached_geolocation", cache_data)
    
    def get_preferred_languages(self) -> List[str]:
        """Get current preferred languages."""
        return self.preferred_languages.copy()
    
    def get_location_info(self) -> Optional[GeolocationResult]:
        """Get current location information."""
        return self.current_location
    
    def set_manual_languages(self, languages: List[str]):
        """Manually set preferred languages (overrides geolocation)."""
        self.preferred_languages = languages
        self.settings_manager.set_setting("manual_subtitle_languages", languages)
        self.preferred_languages_changed.emit(self.preferred_languages)
    
    def is_auto_detection_enabled(self) -> bool:
        """Check if auto-detection is enabled."""
        auto_detect = self.settings_manager.get_setting("geolocation_auto_detect")
        return auto_detect if auto_detect is not None else True

    def set_auto_detection_enabled(self, enabled: bool):
        """Enable or disable auto-detection."""
        self.settings_manager.set_setting("geolocation_auto_detect", enabled)
        if enabled:
            self._setup_auto_detection()
        else:
            self.auto_detection_timer.stop()
    
    def stop_auto_detection(self):
        """Stop automatic location detection."""
        self.auto_detection_timer.stop()
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.terminate()
            self.detection_thread.wait()
