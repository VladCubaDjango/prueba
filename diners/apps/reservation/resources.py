from import_export import resources

from .models import Reservation, DishCategory, Dish, Menu


class ReservationResource(resources.ModelResource):

    def get_fields(self):
        fields = super(ReservationResource, self).get_fields()
        new_fields = [field for field in fields if field.attribute not in ['id']]
        return new_fields

    class Meta:
        model = Reservation


class DishCategoryResource(resources.ModelResource):
    class Meta:
        model = DishCategory


class DishResource(resources.ModelResource):
    class Meta:
        model = Dish


class MenuResource(resources.ModelResource):
    class Meta:
        model = Menu
