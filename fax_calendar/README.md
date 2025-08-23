# FAX Woorld kalendář

Tato aplikace poskytuje widget a pole pro práci s Woorld kalendářem
s 15 měsíci střídajícími se v délce 29/28 dnů. Datum se zadává ve formátu
`DD/MM/YYYY` a v databázi se ukládá jako řetězec `YYYY-MM-DDw`.

Použití mimo admin:

```python
from fax_calendar.fields import WoorldDateFormField

class MyForm(forms.Form):
    datum = WoorldDateFormField(required=False)
```
