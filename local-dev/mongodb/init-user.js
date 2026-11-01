db.getSiblingDB('admin').createUser({
  user: 'quantaxis',
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: ['quantaxis', 'qascheduler', 'QAREALTIME'].map(name => ({role: 'readWrite', db: name}))
});
