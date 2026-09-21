# Contrat MQTT Yggdrasil — EIR

## Topics publies par EIR

### `yggdrasil/eir/alert/crisis`

Declenchement crise epidemique (15 % ou ratio configure).

```json
{
  "level": "epidemic",
  "sick_ratio": 0.15,
  "autonomy_days": 9
}
```

### `yggdrasil/eir/stock/low`

Stock critique ou zero.

```json
{
  "drug_id": "paracetamol",
  "remaining_units": 0
}
```

## Topic ecoute (MIMIR)

### `yggdrasil/mimir/security/infirmary`

Alerte securite reseau infirmerie (ex. falsification stock). EIR enregistre dans `security_alerts` et expose `GET /api/security/alerts`.

Exemple simulateur local :

```json
{
  "alert": "stock_tampering",
  "drug_id": "paracetamol",
  "message": "Tentative de falsification des donnees de stock infirmerie"
}
```

Commande test :

```powershell
python tools/mqtt-simulate-mimir.py localhost
```

## Alignement equipe MIMIR

A valider mercredi avec l equipe MIMIR : QoS 1, broker Mosquitto partage, format JSON UTF-8.
