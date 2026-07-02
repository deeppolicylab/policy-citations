# Policy Citation Dashboard

Static dashboard for policy citation using data from Sage Policy Profiles.


## Use this repository to create your own policy citation dashboard

1. `Star` this repository for future refrence
1. `Fork` to create your own repository
1. Download the export data from your Sage Policy Profiles and replace the `policy-impact-export.csv`
1. Run `python3 update-dashboard-data.py` to update the `dashboard-data.js` with your own data
1. Open `index.html` and enjoy your dashboard
1. You can customize colors, backgrounds, and other styles of your dashboard in `theme.scss`


## Update the dashboard

This steps currently can only done manually as Sage Policy Profiles does not allow auto data download. 

1. Download the latest `policy-impact-export.csv` from your Sage Policy Profiles. Delete the auto generated date from the file name.
1. Replace `policy-impact-export.csv` with the downloaded file.
1. Run:

```sh
python3 update-dashboard-data.py
```

This regenerates `dashboard-data.js`, which is loaded by `index.html`.

## Preview locally

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

Or open the `index.html` file directly. 

## Files

- `index.html` is the dashboard UI.
- `policy-impact-export.csv` is the current source export.
- `dashboard-data.js` is generated from the CSV.
- `update-dashboard-data.py` converts the export into dashboard data.
