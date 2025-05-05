from .models import Country
from .serializers import CountryListSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
# Create your views here.

#list of all Country
class CountryList(APIView):
    def get(self,request,*args,**kwargs):
        countrylist=Country.objects.all()
        serializer=CountryListSerializer(instance=countrylist,many=True)
        return Response(serializer.data)
