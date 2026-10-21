"""Task and contrast vocabulary from the Cognitive Atlas API."""


class CognitiveAtlasGateway:
    def tasks(self):
        """[(task id, name, [(contrast id, name), ...]), ...]"""
        from cognitiveatlas.api import get_task

        out = []
        tasks = get_task().json
        for t, task in enumerate(tasks):
            print("%s of %s" % (t, len(tasks)))
            if not task["name"]:
                continue
            contrasts = []
            if task["id"]:
                details = get_task(id=task["id"]).json
                if details["contrasts"]:
                    print("Found %s contrasts!" % len(details["contrasts"]))
                    contrasts = [(c["id"], c["name"]) for c in details["contrasts"]]
            out.append((task["id"], task["name"], contrasts))
        return out
