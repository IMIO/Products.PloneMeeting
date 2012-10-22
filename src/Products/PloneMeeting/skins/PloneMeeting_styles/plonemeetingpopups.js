/* The jQuery here above will load a jQuery popup */

jQuery(function($){

    // Add or edit advice popup
    $('a.link-overlay').prepOverlay({
       subtype: 'ajax',
       urlmatch: '@@addeditadvice',
   });

});
