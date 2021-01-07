from plone import api
from plone.memoize.view import memoize
from Products.Five.browser import BrowserView
from Products.PloneMeeting.utils import getCurrentMeetingObject
from zope.globalrequest import getRequest


class BaseImgSelectBoxView(BrowserView):
    '''Base class to render the selectBox with images, this is made to be overrided.'''

    def __init__(self, context, request):
        super(BaseImgSelectBoxView, self).__init__(context, request)
        self.context = context
        self.request = getRequest()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self, **kwargs):
        """ """
        for k, v in kwargs.items():
            setattr(self, k, v)
        return super(BaseImgSelectBoxView, self).__call__()

    @property
    def select_box_name(self):
        """ """
        return 'img_select_box'

    def has_selected_value(self):
        """ """
        return self.value_name in self.request and self.request.get(self.value_name)

    @property
    def value_name(self):
        """ """
        return 'dummy_value_name'

    def selected_value_html(self):
        """ """
        raise NotImplementedError

    def getSelectableValues(self):
        """ """
        raise NotImplementedError

    def selectable_value_class(self, selectable_value):
        """ """
        css_class = "ploneMeetingSelectItem"
        if selectable_value == self.selected_value():
            css_class += " selected"
        return css_class

    def selectable_value_id(self, selectable_value):
        """ """
        return selectable_value.get('id')

    def selectable_value_name(self, selectable_value):
        """ """
        return selectable_value.get('name')


class AnnexTypeImgSelectBoxView(BaseImgSelectBoxView):
    """ """

    @property
    def select_box_name(self):
        """ """
        return 'annex_type_img_select_box'

    @property
    def value_name(self):
        """ """
        return 'annex_type'

    def selected_value_html(self):
        """ """
        selected_value = self.selected_value()
        return """
<img id="idImage1" src="{0}" alt="" class="ploneMeetingSelectImage" />
<span id="idButtonText1" class="ploneMeetingRef">{1}</span>
""".format(selected_value['img_url'], selected_value['label'])

    @memoize
    def selected_value(self):
        """ """
        annexType = self.request.get('annex_type')
        uid_catalog = api.portal.get_tool('uid_catalog')
        mft = uid_catalog(UID=annexType.split('__subtype__')[0])[0].getObject()
        mftData = '__subtype__' in annexType and mft._dataFor(annexType.split('__subtype__')[1]) or mft._dataFor()
        return {'img_url': mft.absolute_url() + '/theIcon',
                'label': mftData['name']}

    def selectable_value_html(self, num, selectable_value):
        """ """
        return """
<img class="ploneMeetingSelectImage" src="{0}" id="idImage_{1}">
<span>{2}</span>
""".format(selectable_value['absolute_url'] + '/theIcon',
           self.select_box_name + '1' + str(num),
           selectable_value['name'])

    def getSelectableValues(self):
        """ """
        return self.fileTypes

    def selectable_value_class(self, selectable_value):
        """ """
        return '__subtype__' in selectable_value['id'] and 'ploneMeetingSelectItem subtype' or 'ploneMeetingSelectItem'


class GoToMeetingImgSelectBoxView(BaseImgSelectBoxView):
    """ """

    @property
    def select_box_name(self):
        """ """
        return 'go_to_meeting_img_select_box_' + self.select_box_name_suffix

    def has_selected_value(self):
        """ """
        return bool(self.selected_value())

    def selected_value_html(self):
        """ """
        link = self.selected_value().get_pretty_link(
            isViewable=False,
            notViewableHelpMessage=u'',
            link_pattern=u"<span class='pretty_link'{0}>{1}<span class='pretty_link_content{2}'>{3}</span></span>")
        return u"""
<span id="idButtonText_{0}" class="ploneMeetingRef">{1}</span>
""".format(self.select_box_name, link)

    @memoize
    def selected_value(self):
        """ """
        # avoid displaying old Meeting when going to a dashboard (my items, ...)
        if self.request.getURL().endswith('facetednavigation_view'):
            return
        current = getCurrentMeetingObject(self.request)
        if current and current.UID() in [brain.UID for brain in self.brains]:
            return current

    def selectable_value_html(self, num, selectable_value):
        """ """
        return selectable_value.get_pretty_link()

    def getSelectableValues(self):
        """ """
        res = [brain.getObject() for brain in self.brains]
        # reinitialize REQUEST URL because sometimes it is None...
        for obj in res:
            if not obj.REQUEST.get('URL'):
                obj.REQUEST.__dict__ = self.request.__dict__
        return res

    def selectable_value_id(self, selectable_value):
        """ """
        return selectable_value.getId()

    def selectable_value_name(self, selectable_value):
        """ """
        return selectable_value.Title()
