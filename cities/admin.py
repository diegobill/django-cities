from django.contrib import admin
from models import *

class CitiesAdmin(admin.ModelAdmin):
    raw_id_fields = ['alt_names']

    def queryset(self, request):
        """
        Filter the objects displayed in the change_list.
        """
        qs = super(CitiesAdmin, self).queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(deleted=False)

class PlaceAdmin(CitiesAdmin):
    ordering = ['name']
    search_fields = ['name']
    list_display = ['name', 'ranking','slug', 'active', 'geonames']

admin.site.register(Place, PlaceAdmin)

class ContinenteAdmin(CitiesAdmin):
    ordering = ['name']

admin.site.register(Continente, ContinenteAdmin)

class CountryAdmin(CitiesAdmin):
    list_display = ['__str__', 'continent']
    search_fields = ['name', 'code', 'code3', 'tld', 'phone']

admin.site.register(Country, CountryAdmin)

class RegionAdmin(CitiesAdmin):
    ordering = ['name_std']
    list_display = ['__str__', 'country']
    search_fields = ['name', 'name_std', 'code']

admin.site.register(Region, RegionAdmin)

class SubregionAdmin(CitiesAdmin):
    ordering = ['name_std']
    list_display = ['name_std', 'code', 'region']
    search_fields = ['name', 'name_std', 'code']
    raw_id_fields = ['alt_names', 'region']

admin.site.register(Subregion, SubregionAdmin)

#class CityAdmin(CitiesAdmin):
#    ordering = ['name_std']
#    list_display = ['name_std']
#    search_fields = ['name_std']
#    raw_id_fields = ['alt_names']#, 'region', 'subregion']
    #exclude = ['subregion']

#admin.site.register(City, CityAdmin)

class DistrictAdmin(CitiesAdmin):
    raw_id_fields = ['alt_names', 'city']
    list_display = ['name_std', 'city']
    search_fields = ['name', 'name_std']

admin.site.register(District, DistrictAdmin)

class AltNameAdmin(admin.ModelAdmin):
    ordering = ['name']
    list_display = ['name', 'language', 'is_preferred', 'is_short']
    list_filter = ['is_preferred', 'is_short', 'language']
    search_fields = ['name']

admin.site.register(AlternativeName, AltNameAdmin)

class PostalCodeAdmin(CitiesAdmin):
    ordering = ['code']
    list_display = ['code', 'subregion_name', 'region_name', 'country']
    search_fields = ['code', 'country__name', 'region_name', 'subregion_name']

admin.site.register(PostalCode, PostalCodeAdmin)
