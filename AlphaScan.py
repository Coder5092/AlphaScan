import adsk.core, adsk.fusion
import traceback, os
import time, re, json
import urllib.request as requests

app = adsk.core.Application.get()
ui = app.userInterface

cmdDef = None
handlers = []

class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
  def notify(self, args): # type: ignore
    runAlphaScan()

def runAlphaScan():
  try:
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)

    if not design:
      ui.messageBox('No active Fusion design found.', 'Warning', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.WarningIconType) # type: ignore
      return
    
    startTime = time.time()
    this_dir = os.path.dirname(os.path.realpath(__file__))

    def decodeVersionName(name: str):
      data = name.strip().split(' ')[:2]
      release, patch = data
      releaseNo, patch = patch.split('.')
      return 'alpha'.split(' ').index(release.lower()) * 1000 + int(releaseNo) * 100 + int(patch) # type: ignore

    with requests.urlopen("https://raw.githubusercontent.com/Coder5092/AlphaScan/refs/heads/main/AlphaScan.manifest") as response:
      if response is None:
        ui.messageBox('Failed to fetch version information from the internet.\nPress OK to continue scanning', 'Warning', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.WarningIconType) # type: ignore
      else:
        networkManifest = json.load(response)
        networkVersion = networkManifest['version']
        with open(os.path.join(this_dir, "AlphaScan.manifest"), 'r') as file:
          manifest = json.load(file)
          version = manifest['version']

          networkInt = decodeVersionName(networkVersion)
          localInt = decodeVersionName(version)

          if networkInt > localInt:
            ui.messageBox(f'The latest online version of AlphaScan ({networkVersion}) is newer than the current installed version ({version}). Please upgrade AlphaScan!', 'Error', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.CriticalIconType) # type: ignore
            return
          elif networkInt < localInt:
            # How did you even manage this?
            ui.messageBox(f'The latest online version of AlphaScan ({networkVersion}) is older than the current installed version ({version}). Please downgrade AlphaScan!', 'Error', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.CriticalIconType) # type: ignore
            return
    
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
    
    def jointless(occurrence: adsk.fusion.Occurrence, vendor = False):
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
            for j in range(occurrence.childOccurrences.count * vendor):
              if not jointless(occurrence.childOccurrences.item(j), vendor):
                break
            else:
              return True
      return False

    with open(os.path.join(this_dir, "config/config.json"), 'r') as file:
      config = json.load(file)

    # allOccurrences: list[adsk.fusion.Occurrence] = []

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
      # for i in range(occs.count): allOccurrences.append(occs.item(i))

      isGobilda = re.match(r"\d{4}-\d{4}-\d{4}", componentType.name) is not None
      isRev = re.match(r"REV-\d{2}-\d{4}", componentType.name) is not None
      isAndyMark = re.match(r"am-\d{4}(_[a-z]+)?", componentType.name) is not None
      isVendor = isGobilda or isRev or isAndyMark
      if isGobilda: vendorComponents[0] += occs.count
      if isRev: vendorComponents[1] += occs.count
      if isAndyMark: vendorComponents[2] += occs.count

      for i in range(occs.count):
        occurrence = occs.item(i)
        occurrenceCount += 1

        if jointless(occurrence, isVendor):
          message += occurrence.name + ' is not jointed\n'

        if occurrence.isReferencedComponent and isVendor:
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

            hasHoleIssue |= sum(totalSmallHoles.values()) > 0

    # grounded = tuple(filter(lambda o: o.isGrounded and not o.assemblyContext, allOccurrences))
    # reachable: set[str] = set()
    # trace = ""
    # trace = ""

    # nodes = {o.fullPathName: o for o in allOccurrences}
    # adj = defaultdict(set)

    # def link(a, b):
    #   if a is None or b is None:
    #     return
    #   if a.fullPathName == b.fullPathName:
    #     return
    #   adj[a.fullPathName].add(b.fullPathName)
    #   adj[b.fullPathName].add(a.fullPathName)

    # for node in allOccurrences:
    #   try:
    #     for i in range(node.joints.count):
    #       j = node.joints.item(i)
    #       link(j.occurrenceOne, j.occurrenceTwo)
    #   except Exception as e:
    #       trace += f"joints: {e}\n"

    #   try:
    #     for i in range(node.asBuiltJoints.count):
    #       j = node.asBuiltJoints.item(i)
    #       link(j.occurrenceOne, j.occurrenceTwo)
    #   except Exception as e:
    #     trace += f"asBuiltJoints: {e}\n"

    #   try:
    #     for i in range(node.rigidGroups.count):
    #       g = node.rigidGroups.item(i)

    #       members = [g.occurrences.item(j) for j in range(g.occurrences.count)]

    #       for i2 in range(len(members)):
    #         for j2 in range(i2 + 1, len(members)):
    #           link(members[i2], members[j2])
    #   except Exception as e:
    #     trace += f"rigidGroups: {e}\n"

    #   # parent-child rigidity assumption
    #   try:
    #     if node.assemblyContext:
    #       link(node, node.assemblyContext)
    #   except Exception as e:
    #     trace += f"assemblyContext: {e}\n"

    # reachable = set()
    # q = deque()

    # for o in grounded:
    #   key = o.fullPathName
    #   reachable.add(key)
    #   q.append(key)

    # while q:
    #   cur = q.popleft()

    #   for nxt in adj[cur]:
    #     if nxt not in reachable:
    #       reachable.add(nxt)
    #       q.append(nxt)

    # with open(os.path.join(this_dir, 'trace.txt'), 'w') as file:
    #   file.write(trace)

    # for node in filter(lambda o: o.fullPathName not in reachable, allOccurrences):
    #   message += node.name + ' is floating\n'

    # out-of-dates
    refs = app.activeDocument.documentReferences
    if refs:
      for i in range(refs.count):
        reference = refs.item(i)
        if reference.isOutOfDate:
          message += reference.referencedDocument.name + ' is out of date\n'

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
  except:
    ui.messageBox(f'Failed:\n{traceback.format_exc()}', 'Error', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.CriticalIconType) # type: ignore


def run(context):
  global cmdDef

  workspaces = ui.workspaces.itemById('FusionSolidEnvironment')
  panel = workspaces.toolbarPanels.itemById('InspectPanel')

  cmdDef = ui.commandDefinitions.addButtonDefinition(
    'AlphaScanButton',
    'Run AlphaScan',
    'Scans the current CAD file.',
    './assets'
  )

  panel.controls.addCommand(cmdDef) # type: ignore

  onCreated = MyCommandCreatedHandler()
  cmdDef.commandCreated.add(onCreated)
  handlers.append(onCreated)

  # cmdDef.execute() # type: ignore

def stop(context):
  global cmdDef
  try:
    workspace = ui.workspaces.itemById('FusionSolidEnvironment')
    panel = workspace.toolbarPanels.itemById('InspectPanel')

    ctrl = panel.controls.itemById('AlphaScanButton')
    if ctrl:
      ctrl.deleteMe()

    if cmdDef:
      cmdDef.deleteMe()
  except:
    ui.messageBox('Stop failed:\n{}'.format(traceback.format_exc())) # type: ignore