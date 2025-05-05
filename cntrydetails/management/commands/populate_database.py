import json
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from cntrydetails.models import (
    Continent, Currency, Language, Region, Subregion,
    Country, CountryName, Demonym, Border, Capital,
    CountryFlag, CountryCoatOfArms, CountryPostalCode,
    InternationalDialing, CountryCurrency, CountryLanguage,
    TopLevelDomain, AlternativeSpelling, Timezone,
    CarSign, GiniIndex
)
class Command(BaseCommand):
    help = 'Populates database with country data from REST Countries API'
    def handle(self, *args, **options):
        self.stdout.write("Starting population process...")
        
        try:
            # Fetch all countries data
            response = requests.get('https://restcountries.com/v3.1/all')
            # raises an error if status code is not 2xx
            response.raise_for_status()
            #cnverting json Data to python data
            countries_data = response.json()
            
            #maintain data integrity by using .atomoic
            with transaction.atomic():
                self.populate_initial_data(countries_data)
                self.process_countries(countries_data)
                
            self.stdout.write(self.style.SUCCESS('Successfully populated database!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))

    def populate_initial_data(self, countries_data):
        """Create continents, regions, subregions, currencies and languages first"""
        continents = set()
        regions = set()
        subregions = set()
        currencies = {}
        languages = {}

        for country in countries_data:
            # Collect continents
            for continent in country.get('continents', []):
                continents.add(continent)
            
            # Collect regions and subregions
            region = country.get('region')
            subregion = country.get('subregion')
            if region:
                regions.add(region)
            if subregion:
                subregions.add((subregion, region))
            
            # Collect currencies
            for code, currency_data in country.get('currencies', {}).items():
                currencies[code] = {
                    'name': currency_data.get('name'),
                    'symbol': currency_data.get('symbol')
                }
            
            # Collect languages
            for code, name in country.get('languages', {}).items():
                languages[code] = name

        # Create continents
        continent_map = {}
        for name in continents:
            continent, _ = Continent.objects.get_or_create(
                     name=name
                     )
            continent_map[name] = continent

        # Create regions
        region_map = {}
        for name in regions:
            region, _ = Region.objects.get_or_create(name=name)
            region_map[name] = region

        # Create subregions
        subregion_map = {}
        for name, region_name in subregions:
            subregion, _ = Subregion.objects.get_or_create(
                name=name,
                region=region_map[region_name]
            )
            subregion_map[name] = subregion

        # Create currencies
        currency_map = {}
        for code, data in currencies.items():
            currency, _ = Currency.objects.get_or_create(
                code=code,
                defaults={
                    'name': data['name'],
                    'symbol': data['symbol']
                }
            )
            currency_map[code] = currency

        # Create languages
        language_map = {}
        for code, name in languages.items():
            language, _ = Language.objects.get_or_create(
                iso_code=code,
                defaults={'name': name}
            )
            language_map[code] = language

        return {
            'continent_map': continent_map,
            'region_map': region_map,
            'subregion_map': subregion_map,
            'currency_map': currency_map,
            'language_map': language_map
        }

    def process_countries(self, countries_data):
        """Process all countries and their related data"""
        initial_data = self.populate_initial_data(countries_data)
        
        for country_data in countries_data:
            self.process_country(country_data, initial_data)

    def process_country(self, country_data, initial_data):
        """Process a single country and all its relations"""
        # Get or create the country
        country, created = Country.objects.get_or_create(
            cca2=country_data['cca2'],
            defaults={
                'cca3': country_data['cca3'],
                'ccn3': country_data['ccn3'],
                'common_name': country_data['name']['common'],
                'official_name': country_data['name']['official'],
                'independent': country_data.get('independent', False),
                'un_member': country_data.get('unMember', False),
                'status': country_data.get('status', 'user-assigned'),
                'region': initial_data['region_map'].get(country_data.get('region')),
                'subregion': initial_data['subregion_map'].get(country_data.get('subregion')),
                'landlocked': country_data.get('landlocked', False),
                'area': country_data.get('area'),
                'latitude': country_data.get('latlng', [None, None])[0],
                'longitude': country_data.get('latlng', [None, None])[1],
                'population': country_data.get('population', 0),
                'cioc': country_data.get('cioc'),
                'fifa': country_data.get('fifa'),
                'driving_side': country_data.get('car', {}).get('side', 'right'),
                'start_of_week': country_data.get('startOfWeek', 'monday'),
                'google_maps': country_data.get('maps', {}).get('googleMaps', ''),
                'openstreet_maps': country_data.get('maps', {}).get('openStreetMaps', '')
            }
        )

        if not created:
            return  # Skip if country already exists

        # Add continents
        for continent_name in country_data.get('continents', []):
            continent = initial_data['continent_map'].get(continent_name)
            if continent:
                country.continents.add(continent)

        # Process native names and translations
        self.process_names(country, country_data, initial_data['language_map'])

        # Process currencies
        for code, _ in country_data.get('currencies', {}).items():
            currency = initial_data['currency_map'].get(code)
            if currency:
                CountryCurrency.objects.create(country=country, currency=currency)

        # Process languages
        for code, _ in country_data.get('languages', {}).items():
            language = initial_data['language_map'].get(code)
            if language:
                CountryLanguage.objects.create(country=country, language=language)

        # Process other relations
        self.process_demonyms(country, country_data, initial_data['language_map'])
        self.process_borders(country, country_data)
        self.process_capital(country, country_data)
        self.process_flag(country, country_data)
        self.process_coat_of_arms(country, country_data)
        self.process_postal_code(country, country_data)
        self.process_idd(country, country_data)
        self.process_tlds(country, country_data)
        self.process_alt_spellings(country, country_data)
        self.process_timezones(country, country_data)
        self.process_car_signs(country, country_data)
        self.process_gini_index(country, country_data)

    def process_names(self, country, country_data, language_map):
        """Process native names and translations"""
        # Process native names
        native_names = country_data.get('name', {}).get('nativeName', {})
        for lang_code, names in native_names.items():
            language = language_map.get(lang_code)
            if language:
                CountryName.objects.create(
                    country=country,
                    language=language,
                    name_type='native',
                    official=names.get('official', ''),
                    common=names.get('common', '')
                )

        # Process translations
        translations = country_data.get('translations', {})
        for lang_code, names in translations.items():
            language = language_map.get(lang_code)
            if language:
                CountryName.objects.create(
                    country=country,
                    language=language,
                    name_type='translation',
                    official=names.get('official', ''),
                    common=names.get('common', '')
                )

    def process_demonyms(self, country, country_data, language_map):
        """Process demonyms"""
        demonyms = country_data.get('demonyms', {})
        for lang_code, demonym_data in demonyms.items():
            language = language_map.get(lang_code)
            if language:
                Demonym.objects.create(
                    country=country,
                    language=language,
                    male=demonym_data.get('m', ''),
                    female=demonym_data.get('f', '')
                )

    def process_borders(self, country, country_data):
        """Process bordering countries"""
        for border_cca3 in country_data.get('borders', []):
            try:
                neighbor = Country.objects.get(cca3=border_cca3)
                Border.objects.create(country=country, neighbor=neighbor)
            except Country.DoesNotExist:
                continue  # Skip if neighbor doesn't exist yet

    def process_capital(self, country, country_data):
        """Process capital city"""
        capitals = country_data.get('capital', [])
        capital_info = country_data.get('capitalInfo', {}).get('latlng', [None, None])
        
        if capitals:
            Capital.objects.create(
                country=country,
                name=capitals[0],
                latitude=capital_info[0],
                longitude=capital_info[1]
            )

    def process_flag(self, country, country_data):
        """Process flag information"""
        flags = country_data.get('flags', {})
        if flags:
            CountryFlag.objects.create(
                country=country,
                emoji=country_data.get('flag', ''),
                emoji_unicode=self.flag_to_unicode(country_data.get('flag', '')),
                png=flags.get('png', ''),
                svg=flags.get('svg', ''),
                alt=flags.get('alt', '')
            )

    def flag_to_unicode(self, flag_emoji):
        """Convert flag emoji to Unicode code points"""
        if not flag_emoji:
            return ''
        return ' '.join([f"U+{ord(c):04X}" for c in flag_emoji])

    def process_coat_of_arms(self, country, country_data):
        """Process coat of arms"""
        coat_of_arms = country_data.get('coatOfArms', {})
        if coat_of_arms:
            CountryCoatOfArms.objects.create(
                country=country,
                png=coat_of_arms.get('png', ''),
                svg=coat_of_arms.get('svg', '')
            )

    def process_postal_code(self, country, country_data):
        """Process postal code information"""
        postal_code = country_data.get('postalCode', {})
        if postal_code:
            CountryPostalCode.objects.create(
                country=country,
                format=postal_code.get('format'),
                regex=postal_code.get('regex')
            )

    def process_idd(self, country, country_data):
        """Process international dialing data"""
        idd_data = country_data.get('idd', {})
        if idd_data:
            InternationalDialing.objects.create(
                country=country,
                root=idd_data.get('root', ''),
                suffixes=idd_data.get('suffixes', [])
            )

    def process_tlds(self, country, country_data):
        """Process top-level domains"""
        for tld in country_data.get('tld', []):
            TopLevelDomain.objects.create(
                country=country,
                domain=tld
            )

    def process_alt_spellings(self, country, country_data):
        """Process alternative spellings"""
        for spelling in country_data.get('altSpellings', []):
            AlternativeSpelling.objects.create(
                country=country,
                spelling=spelling
            )

    def process_timezones(self, country, country_data):
        """Process timezones"""
        for tz in country_data.get('timezones', []):
            Timezone.objects.create(
                country=country,
                name=tz
            )

    def process_car_signs(self, country, country_data):
        """Process car signs"""
        signs = country_data.get('car', {}).get('signs', [])
        for sign in signs:
            CarSign.objects.create(
                country=country,
                sign=sign
            )

    def process_gini_index(self, country, country_data):
        """Process Gini index data"""
        gini_data = country_data.get('gini', {})
        for year, value in gini_data.items():
            GiniIndex.objects.create(
                country=country,
                year=year,
                value=value
            )