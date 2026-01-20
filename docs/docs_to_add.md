From Leo's email:
Hello! 

Yes, the readme is much better now; I don't think the instructions are complicated, assuming people already know at least one of the manufacturers --- that is, someone will not mistake your software for a drone controller or something totally unrelated!  (You mention the instruments at the top of the readme, and it's clear it's a software for Raman Imaging, so the users know what to expect!). If the user is not familiar ("what's a brightfield camera? what's a spectrometer") then they should have an expert at arm's length, in which case the instructions-based installation becomes easy. 

As for the documentation, usually (github, Open Source) software have a few sections: 
introduction / motivation (describe the problem and solution, like your first paragraph of README)
Installation (with screenshots, in the case of Windows or graphical-based software so you follow the clickety-clicks)
Tutorials (this is IMO the most important, some people learn by example or don't want to explore all possibilities of software); it can include a quick test, with self-contained example files. 
command reference / technical reference (with all options described)
citation and licence (mentioning briefly the liability clause if you want to make sure it's understood) 

Other common sections include 
Troubleshooting & FAQ (based on feedback from users or issues you expect to arise)
quick start guide (with installation and most common usage; for users without patience but "stable" environments or more computer literate).
file formats and pre / post-processing (what is the output, and how do we use it?); links to more example data

These can be added later, I believe. I don't have any reference, but I was suggested two documents on advanced python: https://carpentries-incubator.github.io/python_packaging/ and https://learn.scientific-python.org/development/tutorials/docs/ (link to the section on documentation). 

We usually copy the documentation from other successful software. One example, in my view, of a well-documented OSS is https://pyseer.readthedocs.io/en/master/ (sphynx on readthedocs). 

To answer Mike's question, usually (all?) Open Source licences include a liability clause, like (https://opensource.org/license/bsd-3-clause)

"THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."

In particular, the ORM-IRIS software is licensed under GPL-3 , which has sections 15-17 taking care of that. 

cheers
Leo

Dr Leonardo de Oliveira Martins (he/him)| Tenure Track Fellow
