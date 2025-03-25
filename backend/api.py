from flask import Flask, send_from_directory

class ApiServer(Flask):
    def __init__(self, *args, **kwargs):
        super(ApiServer, self).__init__(*args, **kwargs)
        self.config.update(dict(
    