def execute(photo, area, status='NEEDS_FOOD'):
  report_body = {
    'photo': photo,
    'area': area,
    'status': status 
  }
  result = f'Cat report created with {report_body.values()}'
  return result
