//-*****************************************************************************
//
// Copyright (c) 2009-2011,
//  Sony Pictures Imageworks, Inc. and
//  Industrial Light & Magic, a division of Lucasfilm Entertainment Company Ltd.
//
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
// *       Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
// *       Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
// *       Neither the name of Sony Pictures Imageworks, nor
// Industrial Light & Magic nor the names of their contributors may be used
// to endorse or promote products derived from this software without specific
// prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
//-*****************************************************************************

#include "util.h"
#include "delightAlembicArchive.h"
#include "CreateSceneHelper.h"
#include "CameraHelper.h"
#include "LocatorHelper.h"
#include "MeshHelper.h"
#include "NurbsCurveHelper.h"
#include "NurbsSurfaceHelper.h"
#include "PointHelper.h"
#include "XformHelper.h"

#include <maya/MAngle.h>
#include <maya/MGlobal.h>
#include <maya/MTime.h>
#include <maya/MFileObject.h>

#include <maya/MArrayDataHandle.h>
#include <maya/MFloatPointArray.h>
#include <maya/MFnDoubleArrayData.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MFnVectorArrayData.h>

#include <maya/MFnStringData.h>
#include <maya/MFnMeshData.h>
#include <maya/MFnNurbsCurveData.h>
#include <maya/MFnNurbsSurfaceData.h>

#include <maya/MFnGenericAttribute.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnUnitAttribute.h>

#include <Alembic/AbcCoreHDF5/ReadWrite.h>
#include <Alembic/AbcGeom/Visibility.h>

#include "IObjectDrw.h"

MObject delightAlembicArchive::mTimeAttr;
MObject delightAlembicArchive::mAbcFileNameAttr;

MObject delightAlembicArchive::mStartFrameAttr;
MObject delightAlembicArchive::mEndFrameAttr;

delightAlembicArchive::delightAlembicArchive(void) : mFileInitialized(0), mDebugOn(false)
{
    mCurTime = DBL_MAX;

    // 0 mOutPropArrayAttr
    // 1 mOutTransOpArrayAttr
    // 2 mOutSubDArrayAttr
    // 3 mOutPolyArrayAttr
    // 4 mOutCameraArrayAttr
    // 5 mOutNurbsSurfaceArrayAttr
    // 6 mOutNurbsCurveGrpArrayAttr
    // 7 mOutParticlePosArrayAttr, mOutParticleIdArrayAttr
    // 8 mOutLocatorPosScaleArrayAttr
    mOutRead = std::vector<bool>(9, false);
}

delightAlembicArchive::~delightAlembicArchive() 
{
}

MStatus delightAlembicArchive::initialize()
{
    MStatus status;

    MFnUnitAttribute    uAttr;
    MFnTypedAttribute   tAttr;
    MFnNumericAttribute nAttr;

    // add the input attributes: time, file, sequence time
    mTimeAttr = uAttr.create("time", "tm", MFnUnitAttribute::kTime, 0.0);
    status = uAttr.setStorable(true);
    status = addAttribute(mTimeAttr);

    // input file name
    MFnStringData fileFnStringData;
    MObject fileNameDefaultObject = fileFnStringData.create("");
    mAbcFileNameAttr = tAttr.create("alembicFilename", "fn",
        MFnData::kString, fileNameDefaultObject);
    status = tAttr.setStorable(true);
    status = tAttr.setUsedAsFilename(true);
    status = addAttribute(mAbcFileNameAttr);

    // sequence min and max in frames
    mStartFrameAttr = nAttr.create("startFrame", "sf",
        MFnNumericData::kDouble, 0, &status);
    status = nAttr.setWritable(false);
    status = nAttr.setStorable(true);
    status = addAttribute(mStartFrameAttr);

    mEndFrameAttr = nAttr.create("endFrame", "ef",
        MFnNumericData::kDouble, 0, &status);
    status = nAttr.setWritable(false);
    status = nAttr.setStorable(true);
    status = addAttribute(mEndFrameAttr);

	attributeAffects( mAbcFileNameAttr, mStartFrameAttr );
	attributeAffects( mAbcFileNameAttr, mEndFrameAttr );
    return status;
}

MStatus delightAlembicArchive::compute(const MPlug & plug, MDataBlock & dataBlock)
{
    MStatus status;

    // update the frame number to be imported
    MDataHandle timeHandle = dataBlock.inputValue(mTimeAttr, &status);
    MTime t = timeHandle.asTime();
    double inputTime = t.as(MTime::kSeconds);

    MDataHandle dataHandle = dataBlock.inputValue(mAbcFileNameAttr);
    MFileObject fileObject;
    fileObject.setRawFullName(dataHandle.asString());
    MString fileName = fileObject.resolvedFullName();

    // this should be done only once per file
    if (mFileInitialized == false && MString(m_fileName.c_str()) != fileName)
    {
        mFileInitialized = true;
		m_fileName = fileName.asChar();
	    boost::timer Timer;


        // no caching!
        m_archive = Alembic::Abc::IArchive(Alembic::AbcCoreHDF5::ReadArchive(),
            fileName.asChar(), Alembic::Abc::ErrorHandler::Policy(),
            Alembic::AbcCoreAbstract::ReadArraySampleCachePtr());

        if (!m_archive.valid())
        {
            MString theError = "Cannot read file " + fileName;
            printError(theError);
        }

		std::string appName;
		std::string libraryVersionString;
		Alembic::AbcGeom::uint32_t libraryVersion;
		std::string whenWritten;
		std::string userDescription;
		Alembic::AbcGeom::GetArchiveInfo (m_archive,
						appName,
						libraryVersionString,
						libraryVersion,
						whenWritten,
						userDescription);

		if (appName != "")
		{
			std::cout << "  file written by: " << appName << std::endl;
			std::cout << "  using Alembic : " << libraryVersionString << std::endl;
			std::cout << "  written on : " << whenWritten << std::endl;
			std::cout << "  user description : " << userDescription << std::endl;
			std::cout << std::endl;
		}

		// m_object = Alembic::AbcGeom::IObject( m_archive, Alembic::AbcGeom::kTop );

		m_topObject = Alembic::AbcGeom::IObject( m_archive, Alembic::AbcGeom::kTop );
	    
		std::cout << "Opened archive and top object, creating drawables."
				  << std::endl;

		m_drawable.reset( new IObjectDrw( m_topObject, false ) );
		ABCA_ASSERT( m_drawable->valid(),
					 "Invalid drawable for archive: " << fileName );

		std::cout << "Created drawables, getting time range." << std::endl;
		m_minTime = m_drawable->getMinTime();
		m_maxTime = m_drawable->getMaxTime();

		if ( m_minTime <= m_maxTime )
		{
			std::cout << "\nMin Time: " << m_minTime << " seconds " << std::endl
					  << "Max Time: " << m_maxTime << " seconds " << std::endl
					  << "\nLoading min time." << std::endl;
			m_drawable->setTime( m_minTime );
		}
		else
		{
			std::cout << "\nConstant Time." << std::endl
					  << "\nLoading constant sample." << std::endl;
			m_minTime = m_maxTime = 0.0;
			m_drawable->setTime( 0.0 );
		}

		ABCA_ASSERT( m_drawable->valid(),
					 "Invalid drawable after reading start time" );

		std::cout << "Done opening archive. Elapsed time: "
				  << Timer.elapsed() << " seconds." << std::endl;

		// Bounds have been formed!
		m_bounds = m_drawable->getBounds();
		m_bounds.extendBy(m_drawable->getNonInheritedBounds());
		std::cout << "Bounds at min time: " << m_bounds.min << " to "
				  << m_bounds.max << std::endl;

    }

    dataBlock.setClean(plug);
    return status;
}

//-*****************************************************************************
void setMaterials( float o, bool negMatrix = false )
{
    if ( negMatrix )
    {
        GLfloat mat_front_diffuse[] = { 0.1 * o, 0.1 * o, 0.9 * o, o };
        GLfloat mat_back_diffuse[] = { 0.9 * o, 0.1 * o, 0.9 * o, o };

        GLfloat mat_specular[] = { 1.0, 1.0, 1.0, 1.0 };
        GLfloat mat_shininess[] = { 100.0 };

        glClearColor( 0.0, 0.0, 0.0, 0.0 );
        glMaterialfv( GL_FRONT, GL_DIFFUSE, mat_front_diffuse );
        glMaterialfv( GL_FRONT, GL_SPECULAR, mat_specular );
        glMaterialfv( GL_FRONT, GL_SHININESS, mat_shininess );

        glMaterialfv( GL_BACK, GL_DIFFUSE, mat_back_diffuse );
        glMaterialfv( GL_BACK, GL_SPECULAR, mat_specular );
        glMaterialfv( GL_BACK, GL_SHININESS, mat_shininess );    
    }
    else
    {

        GLfloat mat_specular[] = { 1.0, 1.0, 1.0, 1.0 };
        GLfloat mat_shininess[] = { 100.0 };
        GLfloat mat_front_emission[] = {0.0, 0.0, 0.0, 0.0 };
        GLfloat mat_back_emission[] = {o, 0.0, 0.0, o };

        glClearColor( 0.0, 0.0, 0.0, 0.0 );
        glMaterialfv( GL_FRONT, GL_EMISSION, mat_front_emission );
        glMaterialfv( GL_FRONT, GL_SPECULAR, mat_specular );
        glMaterialfv( GL_FRONT, GL_SHININESS, mat_shininess );

        glMaterialfv( GL_BACK, GL_EMISSION, mat_back_emission );
        glMaterialfv( GL_BACK, GL_SPECULAR, mat_specular );
        glMaterialfv( GL_BACK, GL_SHININESS, mat_shininess );    

        glColorMaterial(GL_FRONT_AND_BACK, GL_DIFFUSE);
        glEnable(GL_COLOR_MATERIAL);
    }
}

void delightAlembicArchive::draw( M3dView & view, const MDagPath & path, 
							 M3dView::DisplayStyle style,
							 M3dView::DisplayStatus display_status )
{ 
	// cout << "delightAlembicArchive::draw\n";

	MStatus		status;
	MObject		thisNode = thisMObject();

	MFnDependencyNode nodeFn(thisNode);
	MPlug timePlug = nodeFn.findPlug("time", &status);
	MTime t = timePlug.asMTime();
    double inputTime = t.as(MTime::kSeconds);

    // update only when the time lapse is big enough
    if (fabs(inputTime - mCurTime) > 0.00001)
    {
        mCurTime = inputTime;
		m_drawable->setTime( mCurTime );

	    setMaterials( 1.0, false );
		m_bounds = m_drawable->getBounds();
		m_bounds.extendBy(m_drawable->getNonInheritedBounds());
    }


    MColor col;
    if (display_status == 8) {
//        col = colorRGB( status );
        col = MColor(0.25,1.0,0.5);
    } else {
        col = MColor(0.7,0.5,0.5);
    }

	view.beginGL(); 
	//view.setDisplayStyle(M3dView::kWireFrame);

	// Push the color settings
	// 
	glPushAttrib(GL_ALL_ATTRIB_BITS);

	//view.setDrawColor(M3dView::kTemplateColor);
    glEnable(GL_LIGHTING);

    glEnable(GL_COLOR_MATERIAL);

    glEnable (GL_BLEND);
    glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    
    glColor3f(col.r,col.g,col.b);
    glFlush();
/*
	if (m_drawable.use_count() > 0)
	{
		DrawContext dctx;
		m_drawable->draw( dctx );
	}
*/
//	glEnd();

	glPopAttrib();

	view.endGL();
}

bool delightAlembicArchive::isBounded() const
{ 
	return false;
}

bool delightAlembicArchive::drawLast() const
{
	return true;
}

bool delightAlembicArchive::excludeAsLocator() const
{
	return true;
}