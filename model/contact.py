import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

class Contact(db.Model):
	def time_ago(self):
		return db.FancyDateTimeDelta(self.created).format()

	def teaser(self, cutoff=100):
		return self.message if len(self.message) < cutoff else '%s...' % self.message[:cutoff]

	new = db.BooleanProperty(whitelisted=True, default=True)
	from_name = db.StringProperty(whitelisted=True, required=True)
	from_email = db.StringProperty(whitelisted=True, required=True)
	subject = db.StringProperty()
	message = db.TextProperty(whitelisted=True, required=True)
	created = db.CreatedDateTimeProperty()
