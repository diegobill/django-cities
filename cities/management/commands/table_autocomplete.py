from django.core.management.base import BaseCommand
from django.db import connections, reset_queries
from ...models import *

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.table_autocomplete()

    def table_autocomplete(self):
        #tabela cache para autocomplete

        #pegando possiveis idiomas
        languages=['en','pt']
        #for l in AlternativeName.objects.raw("SELECT id, language FROM cities_alternativename GROUP BY language"):
        #    languages.append(l.language.encode('utf-8'))

        #cursor.execute("DELETE FROM cities_table_autocomplete WHERE 1;")
        packet_size = 100;
        limit = packet_size
        offset = 0
        places = Place.objects.all()[offset:limit]
        sql_packet=''
        while len(places)>0:
            for place in places:
                for language in languages: 
                    sql = "INSERT INTO cities_table_autocomplete_%s (id, name, slug, active, deleted) VALUES (%s,'%s','%s',%s,%s);" % (
                        language[:2],
                        place.id,
                        place.translated_name(language).replace("'",'"'),
                        place.get_absolute_url(),
                        place.active,
                        place.deleted
                    )
                    sql_packet += sql
            cursor = connections['default'].cursor()
            cursor.execute(sql_packet)
            cursor.close()
            sql_packet=''
            offset+=packet_size
            limit+=packet_size
            # free some memory
            # https://docs.djangoproject.com/en/dev/faq/models/
            reset_queries()
            places = Place.objects.all()[offset:limit]
