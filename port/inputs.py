#Inputs
def report_inputs():
  photo  = input("A photo about case\t")
  area   = input("An area name to tag\t")
  need = input("What should be done?\t")
  return {'photo': photo, 'area': area, 'need': need}

def scan_inputs():
    area   = input("An area name to tag\t")
    return area

def resolve_inputs():
    case_id = input("Case id to resolve\t")
    return case_id