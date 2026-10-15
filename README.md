# Groundtruth

Tells a person, in one plain sentence, how unusual today's weather is for their location compared with its climate-shifted baseline. See `CLAUDE.md` for the project rules.

## Try it

```
pip install -r requirements.txt
python scripts/paiporta.py
```

## Known limitations

- **Past forecasts are short-range.** For past dates we use Open-Meteo's Historical Forecast API. It shows what the models predicted a few hours ahead, not what a forecast issued days ahead said.
- **History is coarser than forecasts.** The 1951-onward history (ERA5) is a ~25 km grid, while forecasts are sharper. A sharp forecast compared with a smoothed history makes today look more extreme, so the comparison leans toward over-warning.

Weather data by Open-Meteo.com
