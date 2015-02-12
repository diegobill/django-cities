from django.utils.encoding import force_unicode
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from conf import settings
from django.db.models import BooleanField
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.db import connections
from django.db import transaction, reset_queries

__all__ = [
        'Point', 'Country', 'Region', 'Subregion',
        'City', 'Continente', 'District', 'PostalCode', 'AlternativeName', 'Place' 
]

def get_or_none(classmodel, **kwargs):
    try:
        return classmodel.objects.get(**kwargs)
    except classmodel.DoesNotExist:
        return None

class Place(models.Model):
    name = models.CharField(max_length=200, db_index=True, verbose_name="ascii name")
    slug = models.CharField(max_length=200)
    alt_names = models.ManyToManyField('AlternativeName', blank=True)

    '''nao aparece mais para a interface do usuario'''
    deleted = BooleanField(default=False, verbose_name=_('deleted'))
    '''
    aparece na interface dos usuarios, mas nao participa das operacoes do sistema 
    exemplo: aparecer na busca de autocomplete, enviar newsletter com esse destino
    '''
    active = BooleanField(default=True, verbose_name=_('active'))
    #indica se aquele place eh oriundo da base do geonames
    #a dica eh fazer a carga inicial da base do geonames ai apartir dai
    #todo novo place tem geonames igual a False
    geonames = BooleanField(default=False, verbose_name=_('geonames'))

    objects = models.GeoManager()

    #utilizado para rankear os places, dessa forma em uma 
    #consulta pode-se ordenar os places segundo esse atributo
    ranking = models.IntegerField()

    #class Meta:
    #    abstract = True

    @property
    def subclass(self):
        for place in [City, District, Subregion, Region, Country, Continente]:
            p = get_or_none(place,pk=self.id) 
            if p:
                return p

        return self

    @property
    def hierarchy(self):
        """Get hierarchy, root first"""
        if isinstance(self,Place):
            subclass = self.subclass
        else:
            subclass = self
        list = subclass.parent.hierarchy if subclass.parent else []
        list.append(subclass)
        return list

    def get_absolute_url(self):
        h = self.hierarchy
        h.reverse()
        return "/".join([place.slug for place in h])

    def get_absolute_slug(self):
        h = self.hierarchy
        return "-".join([place.slug for place in h])

    def translated(self, language=translation.get_language()):
        alts = self.alt_names.filter(
            language__startswith=language[:2], #equiparando idiomas, ISO 639-1 soh possui duas letras
            active=True, 
            deleted=False
        ).order_by('-is_preferred')
        #pega a traducao dando prioridade as is_preferred
        return alts[0] if len(alts)>0 else self

    def __unicode__(self):
        h = self.hierarchy
        h.reverse()
        alt_h=[]
        for p in h:
            language = translation.get_language()
            alt_h.append(p.translated(language))
        return ", ".join([p.name for p in alt_h])

    def translated_name(self,language=translation.get_language()):
        h = self.hierarchy
        h.reverse()
        alt_h=[]
        for p in h:
            alt_h.append(p.translated(language))
        return ", ".join([p.name for p in alt_h])

    #TODO: otimizar consumo de memoria
    def subordinates(self):
        sub = self.subclass
        if type(sub)==City:
            return []
        elif type(sub)==Region:
            cities = City.objects.filter(region__id=self.id)
            return list(cities)
        elif type(sub)==Country:
            cities = City.objects.filter(country__id=self.id)
            regions = Region.objects.filter(country__id=self.id)
            return list(cities)+list(regions)
        elif type(sub)==Continente:
            cities_regions=[]
            countries=Country.objects.filter(continent=sub.code)
            for c in countries:
                cities_regions += c.subordinates()
            return list(countries) + cities_regions

    def update_autocomplete(self, update_subordinates=False):
        orig = Place.objects.get(pk=self.id)

        #atualizando place
        for language in ['pt','en']:
                if 'cities_table_autocomplete_'+language[:2] in connections['default'].introspection.table_names():
                    sql = "UPDATE cities_table_autocomplete_%s SET name='%s', slug='%s', active=%s, deleted=%s, ranking=%s WHERE id=%s;" % (
                        language,
                        self.translated_name(language).replace("'",'"'),
                        self.get_absolute_url(),
                        self.active,
                        self.deleted,
                        self.ranking,
                        self.id
                    )
                    cursor = connections['default'].cursor()
                    cursor.execute(sql)

        #atualizando places subordinados, pois os subordinados possuem o name/slug do superior
        if orig.name!=self.name or orig.slug!=self.slug or update_subordinates:
            places=self.subordinates()
            for language in ['pt','en']:
                if 'cities_table_autocomplete_'+language[:2] in connections['default'].introspection.table_names():
                    for p in places:
                        sql = "UPDATE cities_table_autocomplete_%s SET name='%s', slug='%s' WHERE id=%s;" % (
                            language,
                            p.translated_name(language).replace("'",'"'),
                            p.get_absolute_url(),
                            p.id
                        )
                        cursor = connections['default'].cursor()
                        cursor.execute(sql)

    def save(self, *args, **kwargs):
        #dado alterado passa a nao pertencer mais ao geonames
        self.geonames = False

        super(Place, self).save(*args, **kwargs)

        self.update_autocomplete()

'''
Coloquei continente em portugues, pois quando estava colocando apenas
continent estava dando conflito com o atributo continent de Country.
Continente nao pertence ao geonames.
'''
class Continente(Place):
    code = models.CharField(max_length=2, db_index=True)

    class Meta:
        verbose_name = _('continente')
        verbose_name_plural = _('continentes')

    @property
    def parent(self):
        return None

class Country(Place):
    code = models.CharField(max_length=2, db_index=True)
    code3 = models.CharField(max_length=3, db_index=True)
    population = models.IntegerField(blank=True)
    area = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)
    currency_name = models.CharField(max_length=50, null=True, blank=True)
    languages = models.CharField(max_length=250, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    continent = models.CharField(max_length=2)
    tld = models.CharField(max_length=5)
    capital = models.CharField(max_length=100, blank=True)
    neighbours = models.ManyToManyField("self", blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "countries"

    @property
    def parent(self):
        return Continente.objects.get(code=self.continent)

class Region(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    code = models.CharField(max_length=200, db_index=True)
    country = models.ForeignKey(Country)

    @property
    def parent(self):
        return self.country

    def full_code(self):
        return ".".join([self.parent.code, self.code])

class Subregion(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    code = models.CharField(max_length=200, db_index=True)
    region = models.ForeignKey(Region)

    @property
    def parent(self):
        return self.region

    def full_code(self):
        return ".".join([self.parent.parent.code, self.parent.code, self.code])

class City(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    location = models.PointField()
    population = models.IntegerField(blank=True)
    region = models.ForeignKey(Region, null=True, blank=True)
    subregion = models.ForeignKey(Subregion, null=True, blank=True)
    country = models.ForeignKey(Country)
    elevation = models.IntegerField(null=True, blank=True)
    kind = models.CharField(max_length=10) # http://www.geonames.org/export/codes.html
    timezone = models.CharField(max_length=40) 

    objects = models.GeoManager()

    class Meta:
        verbose_name_plural = "cities"

    @property
    def parent(self):
        return self.region

class District(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    location = models.PointField()
    population = models.IntegerField()
    city = models.ForeignKey(City)

    @property
    def parent(self):
        return self.city

class AlternativeName(models.Model):
    name = models.CharField(max_length=256)
    language = models.CharField(max_length=100)
    is_preferred = models.BooleanField(default=False)
    is_short = models.BooleanField(default=False)
    is_colloquial = models.BooleanField(default=False)

    '''nao aparece mais para a interface do usuario'''
    deleted = BooleanField(default=False, verbose_name=_('deleted'))
    '''
    aparece na interface dos usuarios, mas nao participa das operacoes do sistema 
    exemplo: aparecer na busca de autocomplete, enviar newsletter com esse destino
    '''
    active = BooleanField(default=True, verbose_name=_('active'))
    #indica se aquele dado eh oriundo da base do geonames
    #a dica eh fazer a carga inicial da base do geonames ai apartir dai
    #todo novo dado tem geonames igual a False
    geonames = BooleanField(default=False, verbose_name=_('geonames'))

    def __unicode__(self):
        place = Place.objects.filter(alt_names__id=self.id)
        return place[0].__unicode__()

    def save(self, *args, **kwargs):
        #dado alterado passa a nao pertencer mais ao geonames
        self.geonames = False

        orig = AlternativeName.objects.get(pk=self.id)

        super(AlternativeName, self).save(*args, **kwargs)

        place = Place.objects.get(alt_names__id=self.id)
        place.update_autocomplete(True if orig.name!=self.name else False)

class PostalCode(Place):
    code = models.CharField(max_length=20)
    location = models.PointField()

    country = models.ForeignKey(Country, related_name = 'postal_codes')

    # Region names for each admin level, region may not exist in DB
    region_name = models.CharField(max_length=100, db_index=True)
    subregion_name = models.CharField(max_length=100, db_index=True)
    district_name = models.CharField(max_length=100, db_index=True)

    objects = models.GeoManager()

    @property
    def parent(self):
        return self.country

    @property
    def name_full(self):
        """Get full name including hierarchy"""
        return u', '.join(reversed(self.names)) 

    @property
    def names(self):
        """Get a hierarchy of non-null names, root first"""
        return [e for e in [
            force_unicode(self.country),
            force_unicode(self.region_name),
            force_unicode(self.subregion_name),
            force_unicode(self.district_name),
            force_unicode(self.name),
        ] if e]

    def __unicode__(self):
        return force_unicode(self.code)
