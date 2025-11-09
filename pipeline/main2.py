from crewai.flow.flow import Flow, listen, start, router, and_, or_
from pydantic import BaseModel


class ConmtentPipelineState(BaseModel):
    #inputs
    content_type: str = ""
    topic: str = ""
    #internal
    max_length: int = 0
    score: int = 0

    #coontent
    blog_post: str = ""
    tweet: str = ""
    linkedin_post :str = ""

class contentPipelineFlow(Flow[ConmtentPipelineState]):
    @start()
    def init_conten_pipeline(self):
        # print(self.state.content_type)
        # print(self.state.topic)
        if self.state.content_type not in ["tweet",'blog','linkedin']:
            raise ValueError("The conten type is wrong")

        if self.topic == "":
            raise ValueError("The Topic can't be blank.")

        if self.state.content_type =="tweet":
            self.state.max_length = 150
        elif self.state.content_type == "blog":
            self.state.max_length = 800
        elif self.state.content_type =="linkedin":
            self.state.max_length = 500



    @listen(init_conten_pipeline)
    def conduct_research(self):
        print("Researching...")
        return True
    @router(conduct_research)
    def conduct_research_router(self):
        content_type = self.state.content_type
        if content_type =="blog":
            return "make_blog"
        elif content_type =="tweet":
            return "make_tweet"
        else: 
            return "make_linkedin_post"


    @listen(or_("make_blog","remake_blog"))
    def handle_make_blog(slef):
        #if blog post has been made, show  teh old one to the ai and  ask it to improve, else 
        #just ask to create.
        print("Making blog post....")

    @listen(or_("make_tweet","remake_tweet"))
    def handle_make_tweet(self):
        #if tweet post has been made, show  teh old one to the ai and  ask it to improve, else 
        #just ask to create.
        print("Making tweet post....")
        
    @listen(or_("make_linkedin_post","remake_linkedin_post"))
    def handle_make_Linkedin(self):
        #if linkedin post has been made, show  teh old one to the ai and  ask it to improve, else 
        #just ask to create.
        print("Making Linkedin post....")

    @listen(handle_make_blog)
    def check_seo(self):
        print("Checking Blog SEO")

    @listen(or_(handle_make_tweet,handle_make_Linkedin))
    def check_virality(self):
        print("Checking virality....")


    # @listen(or_(check_seo,check_virality))
    # def finalize_content(self):
    #     print("Finalizing content")

    @router(or_(check_seo,check_virality))
    def score_router(self):
        content_type = self.state.content_type
        score = self.state.score
        
        if score >= 8:
            return "check_passed"
        else:
            if content_type =="blog":
                return "remake_blog"
            elif content_type =="linkedin":
                return "remake_linkedin_post"
            else:
                return "remake_tweet"

    @listen("check_passed")
    def finalize_content(self):
        print("Finalizing content")



flow = contentPipelineFlow()
# flow.kickoff(inputs={
#     "content_type":"tweet",
#     "topic":"AI Dog Training",
#     }, 
# )

flow.plot()