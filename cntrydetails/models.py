from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Language(models.Model):
    iso_code = models.CharField(max_length=3, primary_key=True)  # ISO 639-3
    name = models.CharField(max_length=50)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.iso_code})"

class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)  # ISO 4217
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10, null=True, blank=True)
    
    def __str__(self):
        return f"{self.code} ({self.name})"

class Region(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Subregion(models.Model):
    name = models.CharField(max_length=50, unique=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='subregions')
    
    def __str__(self):
        return f"{self.name} ({self.region})"

class Continent(models.Model):
    name = models.CharField(max_length=20, unique=True)  # Use name as primary key
    
    def __str__(self):
        return self.name

class Country(models.Model):
    class WeekStart(models.TextChoices):
        MONDAY = 'monday', 'Monday'
        TUESDAY = 'tuesday', 'Tuesday'
        WEDNESDAY = 'wednesday', 'Wednesday'
        THURSDAY = 'thursday', 'Thursday'
        FRIDAY = 'friday', 'Friday'
        SATURDAY = 'saturday', 'Saturday'
        SUNDAY = 'sunday', 'Sunday'

    class DrivingSide(models.TextChoices):
        LEFT = 'left', 'Left'
        RIGHT = 'right', 'Right'

    # Core identifiers
    cca2 = models.CharField(max_length=2, primary_key=True)  
    cca3 = models.CharField(max_length=3, unique=True)       
    ccn3 = models.CharField(max_length=3, null=True, blank=True)
    
    # Names
    common_name = models.CharField(max_length=100)
    official_name = models.CharField(max_length=200)
    
    # Status
    independent = models.BooleanField(default=False)
    un_member = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=[
        ('officially-assigned', 'Officially Assigned'),
        ('user-assigned', 'User Assigned')
    ])
    
    # Geography
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    subregion = models.ForeignKey(Subregion, on_delete=models.PROTECT,null=True,
        blank=True,
        related_name='countries')
    continents = models.ManyToManyField(Continent)
    landlocked = models.BooleanField(default=False)
    area = models.FloatField(null=True, blank=True)  # km²
    
    # Coordinates
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    
    # Demographics
    population = models.PositiveBigIntegerField()
    
    # International organizations
    cioc = models.CharField(max_length=3, null=True, blank=True)
    fifa = models.CharField(max_length=3, null=True, blank=True)
    
    # Transportation
    driving_side = models.CharField(max_length=5, choices=DrivingSide.choices)
    
    # Time
    start_of_week = models.CharField(
        max_length=9,
        choices=WeekStart.choices,
        default=WeekStart.MONDAY
    )
    
    # External references
    google_maps = models.URLField(max_length=500)
    openstreet_maps = models.URLField(max_length=500)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['common_name']
        indexes = [
            models.Index(fields=['common_name']),
            models.Index(fields=['official_name']),
            models.Index(fields=['region', 'subregion']),
        ]

    def __str__(self):
        return self.common_name

class CountryName(models.Model):
    class NameType(models.TextChoices):
        NATIVE = 'native', 'Native Name'
        TRANSLATION = 'translation', 'Translation'

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='names')
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    name_type = models.CharField(max_length=11, choices=NameType.choices)
    official = models.CharField(max_length=200)
    common = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('country', 'language', 'name_type')
        verbose_name_plural = "Country Names"

    def __str__(self):
        return f"{self.common} ({self.language})"

class Demonym(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='demonyms')
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    male = models.CharField(max_length=50)
    female = models.CharField(max_length=50)
    
    class Meta:
        unique_together = ('country', 'language')
        verbose_name_plural = "Demonyms"

class Border(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='borders'
    )
    neighbor = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name='bordered_by'
    )
    
    class Meta:
        unique_together = ('country', 'neighbor')

class Capital(models.Model):
    country = models.OneToOneField(
        Country,
        on_delete=models.CASCADE,
        related_name='capital'
    )
    name = models.CharField(max_length=100)
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    
    def __str__(self):
        return f"{self.name} ({self.country.cca3})"

class CountryFlag(models.Model):
    country = models.OneToOneField(
        Country,
        on_delete=models.CASCADE,
        related_name='flag'
    )
    emoji = models.CharField(max_length=15)
    emoji_unicode = models.CharField(max_length=20)
    png = models.URLField(max_length=500)
    svg = models.URLField(max_length=500)
    alt = models.TextField(blank=True)
    
    def __str__(self):
        return f"Flag of {self.country}"

class CountryCoatOfArms(models.Model):
    country = models.OneToOneField(
        Country,
        on_delete=models.CASCADE,
        related_name='coat_of_arms'
    )
    png = models.URLField(max_length=500)
    svg = models.URLField(max_length=500)
    
    def __str__(self):
        return f"Coat of Arms of {self.country}"

class CountryPostalCode(models.Model):
    country = models.OneToOneField(
        Country,
        on_delete=models.CASCADE,
        related_name='postal_code'
    )
    format = models.CharField(max_length=100, null=True, blank=True)
    regex = models.CharField(max_length=200, null=True, blank=True)
    
    def __str__(self):
        return f"Postal codes for {self.country}"

class InternationalDialing(models.Model):
    country = models.OneToOneField(
        Country,
        on_delete=models.CASCADE,
        related_name='idd'
    )
    root = models.CharField(max_length=5)  # e.g. "+2"
    suffixes = models.JSONField()          # List of suffix strings
    
    def __str__(self):
        return f"IDD for {self.country}"

class CountryCurrency(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='currencies'
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT
    )
    
    class Meta:
        unique_together = ('country', 'currency')
        verbose_name_plural = "Country Currencies"

class CountryLanguage(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='languages'
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT
    )
    
    class Meta:
        unique_together = ('country', 'language')

class TopLevelDomain(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='tlds'
    )
    domain = models.CharField(max_length=10)  # e.g. ".bw"
    
    class Meta:
        unique_together = ('country', 'domain')
        verbose_name_plural = "Top Level Domains"

class AlternativeSpelling(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='alt_spellings'
    )
    spelling = models.CharField(max_length=200)
    
    class Meta:
        unique_together = ('country', 'spelling')

class Timezone(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='timezones'
    )
    name = models.CharField(max_length=20)  # e.g. "UTC+02:00"
    
    class Meta:
        unique_together = ('country', 'name')

class CarSign(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='car_signs'
    )
    sign = models.CharField(max_length=10)
    
    class Meta:
        unique_together = ('country', 'sign')

class GiniIndex(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='gini_indices'
    )
    year = models.PositiveSmallIntegerField()
    value = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    class Meta:
        unique_together = ('country', 'year')
        verbose_name_plural = "Gini Indices"
    
    def __str__(self):
        return f"{self.country} ({self.year}): {self.value}"