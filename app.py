from usecases import report_cat_status, scan_cats

#report inputs 
inputs = {
  'photo': '~/Downloads/Sacvan.jpg',
  'area': 'Mayakovski 1'
}

report_cat_status.execute(photo, area)

