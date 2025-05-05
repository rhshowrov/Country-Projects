from rest_framework import serializers
from .models import Country 

class CountryListSerializer(serializers.ModelSerializer):
    class Meta:
        model=Country
        fields=['common_name','official_name']