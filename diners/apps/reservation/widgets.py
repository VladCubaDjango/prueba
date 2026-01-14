from django.forms import SelectMultiple


class DishesMultipleWidget(SelectMultiple):
    def __init__(self, *args, **kwargs):
        self._disabled_choices = []
        super().__init__(*args, **kwargs)

    @property
    def disabled_choices(self):
        return self._disabled_choices

    @disabled_choices.setter
    def disabled_choices(self, other):
        self._disabled_choices = other

    def create_option(self, *args, **kwargs):
        option_dict = super().create_option(*args, **kwargs)
        option_dict['attrs']['data-price'] = int(option_dict['value'].instance.price)
        if option_dict['value'] in self.disabled_choices:
            option_dict['attrs']['disabled'] = 'disabled'
        return option_dict
