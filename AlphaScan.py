"""This file acts as the main module for this script."""

import adsk.core
import adsk.fusion
import traceback, time, os, re, json

app = adsk.core.Application.get()
ui  = app.userInterface


def run(_context: str):
  """This function is called by Fusion when the script is run."""

  try:
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)

    if not design:
      ui.messageBox('No active Fusion design found.', 'Error', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.WarningIconType) # type: ignore
      return
    
    startTime = time.time()
    
    components = design.allComponents
    assemblies = design.rootComponent.allJoints
    sketches = design.rootComponent.sketches

    message = f"""
========== STATISTICS ==========
Total unique components: {components.count}
$total occurrences
$linked component count
$body count
$edge count
Total relationships: {len(assemblies)}
Total sketches: {sketches.count}
$gobildaComponents
$revComponents
$andymarkComponents

========== ISSUES ==========
""".strip() + '\n'

    for i in range(sketches.count):
      sketch = sketches.item(i)
      if not sketch.isFullyConstrained:
        message += sketch.name + ' is not fully constrained\n'
    
    def jointless(occurrence: adsk.fusion.Occurrence):
      count = 0
      try:
        count += occurrence.joints.count
      except:
        pass
      try:
        count += occurrence.asBuiltJoints.count
      except:
        pass
      try:
        count += occurrence.rigidGroups.count
      except:
        pass

      if count == 0:
          if not occurrence.isGrounded:
            if not occurrence.assemblyContext:
              for j in range(occurrence.childOccurrences.count):
                if not jointless(occurrence.childOccurrences.item(j)):
                  break
              else:
                return True
      return False

    this_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(this_dir, "config/config.json"), 'r') as file:
      config = json.load(file)

    hasHoleIssue = False
    linkedComponents = 0
    bodyCount = 0
    edgeCount = 0
    occurrenceCount = 0
    vendorComponents = [0, 0, 0]
    circleType = adsk.core.Circle3D.classType()
    for i in range(components.count):
      componentType = components.item(i)
      if componentType == design.rootComponent:
        pass
      if not componentType.isValid:
        message += componentType.name + ' is invalid\n'
        continue

      occs = design.rootComponent.occurrencesByComponent(componentType)
      isGobilda = re.match(r"\d{4}-\d{4}-\d{4}", componentType.name) is not None
      isRev = re.match(r"REV-\d{2}-\d{4}", componentType.name) is not None
      isAndyMark = re.match(r"am-\d{4}(_[a-z]+)?", componentType.name) is not None
      if isGobilda: vendorComponents[0] += occs.count
      if isRev: vendorComponents[1] += occs.count
      if isAndyMark: vendorComponents[2] += occs.count

      for i in range(occs.count):
        occurrence = occs.item(i)
        occurrenceCount += 1

        if jointless(occurrence):
          message += occurrence.name + ' is not jointed\n'

        if occurrence.isReferencedComponent and (isGobilda or isRev or isAndyMark):
          linkedComponents += 1
        else:
          bodies = list(filter(lambda body: body.isSolid, [occurrence.bRepBodies.item(i) for i in range(occurrence.bRepBodies.count)]))
          bc = len(bodies)
          bodyCount += bc
          if bc == 0 and occurrence.childOccurrences.count == 0:
            message += 'No bodies in ' + occurrence.name + '\n'

          for body in bodies:
            if body.volume == 0:
              message += body.name + ' in component ' + occurrence.name + ' has no volume\n'

            totalSmallHoles = {hole['name']: 0 for hole in config['holes']}
            ec = body.edges.count
            edgeCount += ec
            if ec == 0:
              message += body.name + ' in component ' + occurrence.name + ' has no edges\n'

            for k in range(ec):
              edge = body.edges.item(k).geometry
              if edge is None:
                continue
              if edge.objectType == circleType:
                for hole in config['holes']:
                  if abs(hole['sizeCm'] - edge.radius) < hole['minClearance']: # type: ignore
                    totalSmallHoles[hole['name']] += 1
            
            for i, (name, amt) in enumerate(totalSmallHoles.items()):
              if amt > 0:
                message += body.name + ' in component ' + occurrence.name + f' has {amt} {name} hole{"s" if amt != 1 else ""} that have too low diametrical clearance (minimum {config["holes"][i]["minClearance"] * 10} mm)\n'

            hasHoleIssue = sum(totalSmallHoles.values())
    
    refs = app.activeDocument.documentReferences
    if refs:
      if any([refs.item(i).isOutOfDate for i in range(refs.count)]):
        message += 'Some references are out of date\n'

    message = message.strip()
    message += '\n\n========== OTHER ==========\n'
    if all([sketches.item(i).isFullyConstrained for i in range(sketches.count)]):
      message += 'All sketches fully constrained\n'
    if not hasHoleIssue:
      message += 'No hole issues\n'

    message = message.strip()
    message += f'\n\nCompleted in {time.time() - startTime:.2f} seconds'

    message = message.replace('$total occurrences', f'Total components: {occurrenceCount}')
    message = message.replace('$linked component count', f'Total linked components: {linkedComponents}', 1)
    message = message.replace('$body count', f'Total bodies: {bodyCount}', 1)
    message = message.replace('$edge count', f'Total edges: {edgeCount}', 1)
    message = message.replace('$gobildaComponents', f'Total GoBILDA components: {vendorComponents[0]}', 1)
    message = message.replace('$revComponents', f'Total REV components: {vendorComponents[1]}', 1)
    message = message.replace('$andymarkComponents', f'Total AndyMark components: {vendorComponents[2]}', 1)

    palettes = ui.palettes
    palette = palettes.itemById('scrollable_message_palette')

    with open(os.path.join(this_dir, "assets/template.html"), 'r') as file:
      html_path = os.path.join(this_dir, "assets/scrollable.html")
      with open(html_path, 'w') as output:
        output.write(file.read().replace('$longText', message, 1))

    if palette:
      palette.deleteMe()

    # if not palette:
    palette = palettes.add(
      'scrollable_message_palette',
      "AlphaScan Results",
      html_path.replace('\\', '/'),
      False, True, True, 500, 400
    ) # type: ignore
    
    if '\\' in palette.htmlFileURL:
      palette.htmlFileURL = palette.htmlFileURL.replace('\\', '/')

    palette.isVisible = True
    palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
    # ui.messageBox(message, 'AlphaScan Results', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.InformationIconType) # type: ignore
  except:
    ui.messageBox(f'Failed:\n{traceback.format_exc()}') # type: ignore
