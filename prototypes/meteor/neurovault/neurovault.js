Files = new Meteor.Collection("files")

if (Meteor.isClient) {


Template.home.files = function () {
    return Files.find();
  };

  Template.home.events({
    'click input' : function () {
      filepicker.setKey("AZ6jquGnNSQOt51dbpmvCz");
      filepicker.pick({
      mimetypes: ['image/*', 'text/plain'],
      container: 'window',
      services:['COMPUTER', 'FACEBOOK', 'GMAIL'],
      },
      function(FPFile){
        Files.insert({filename: FPFile.filename, url: FPFile.url})
        console.log(JSON.stringify(FPFile));
      },
      function(FPError){
        console.log(FPError.toString());
      }
      );
      // template data, if any, is available in 'this'
      if (typeof console !== 'undefined')
        console.log("You pressed the button!");
    }
  });
}

if (Meteor.isServer) {
  Meteor.startup(function () {
  });
}
